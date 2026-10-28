"""Render this personal INI's select/fallback groups and ordered rules; never load nodes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parent
INI = ROOT / 'ACL4SSR_Online_Full_Personal_NoAuto.ini'
UI = ROOT / 'group-ui.yaml'

# Fallback groups use the first member whose health check passes, so member order is
# the priority order. The INI may override the test URL and interval; the remaining
# health-check fields live here so one place decides how fast a dead member is skipped.
FALLBACK_URL = 'https://www.gstatic.com/generate_204'
FALLBACK_INTERVAL = 120
FALLBACK_LAZY = False
FALLBACK_TIMEOUT = 3000
FALLBACK_MAX_FAILED_TIMES = 2


@dataclass(frozen=True)
class Group:
    name: str
    choices: tuple[str, ...]
    expression: str | None
    kind: str = 'select'
    url: str | None = None
    interval: int | None = None


@dataclass(frozen=True)
class Rule:
    policy: str
    source: str


def load_policy(path: Path) -> tuple[list[Group], list[Rule]]:
    groups: list[Group] = []
    rules: list[Rule] = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith((';', '#', '[')):
            continue
        key, value = line.split('=', 1)
        if key == 'ruleset':
            policy, source = value.split(',', 1)
            if not source.startswith(('https://', '[]')):
                raise ValueError(f'Unsupported ruleset: {source}')
            rules.append(Rule(policy, source))
        elif key == 'custom_proxy_group':
            name, kind, *members = value.split('`')
            if kind not in ('select', 'fallback'):
                raise ValueError(f'Unsupported group type: {name} ({kind})')
            choices = tuple(member[2:] for member in members if member.startswith('[]'))
            extras = [member for member in members if not member.startswith('[]')]
            if kind == 'select':
                if len(extras) > 1 or not (choices or extras):
                    raise ValueError(f'Unsupported group members: {name}')
                groups.append(Group(name, choices, extras[0] if extras else None))
            else:
                if len(choices) < 2:
                    raise ValueError(f'Fallback group needs at least two members: {name}')
                if len(extras) > 2 or (extras and not extras[0].startswith(('https://', 'http://'))):
                    raise ValueError(f'Unsupported fallback fields: {name}')
                groups.append(Group(
                    name, choices, None, kind='fallback',
                    url=extras[0] if extras else FALLBACK_URL,
                    interval=int(extras[1]) if len(extras) > 1 else FALLBACK_INTERVAL,
                ))
        elif key not in ('enable_rule_generator', 'overwrite_original_rules'):
            raise ValueError(f'Unsupported INI field: {key}')
    names = {group.name for group in groups}
    if len(names) != len(groups):
        raise ValueError('Duplicate group names')
    known = names | {'DIRECT', 'REJECT'}
    for group in groups:
        if any(choice not in known for choice in group.choices):
            raise ValueError(f'Unknown group reference: {group.name}')
    if any(rule.policy not in known for rule in rules):
        raise ValueError('Unknown rule policy')
    if not rules or rules[-1].source != '[]FINAL':
        raise ValueError('The last rule must be FINAL')
    return groups, rules


def build() -> None:
    groups, rules = load_policy(INI)
    ui = yaml.safe_load(UI.read_text(encoding='utf-8'))
    ui_groups = ui.get('groups', {})
    if not isinstance(ui_groups, dict):
        raise ValueError('group-ui.yaml groups must be a mapping')
    policy_names = {group.name for group in groups}
    if set(ui_groups) != policy_names:
        missing = sorted(policy_names - set(ui_groups))
        extra = sorted(set(ui_groups) - policy_names)
        raise ValueError(f'UI metadata does not match policy groups; missing={missing}, extra={extra}')
    config = yaml.safe_load((ROOT / 'mihomo-base.yaml').read_text(encoding='utf-8'))
    if any(key in config for key in ('proxies', 'proxy-providers', 'secret')):
        raise ValueError('The base must not contain nodes or credentials')
    config.update({'proxies': None, 'proxy-groups': [], 'rules': [], 'rule-providers': {}})
    for group in groups:
        item = {'name': group.name, 'type': group.kind}
        metadata = ui_groups[group.name]
        if not isinstance(metadata, dict) or not metadata.get('icon'):
            raise ValueError(f'UI metadata needs an icon: {group.name}')
        item['icon'] = metadata['icon']
        if metadata.get('hidden'):
            item['hidden'] = True
        if group.choices:
            item['proxies'] = list(group.choices)
        if group.kind == 'fallback':
            item['url'] = group.url
            item['interval'] = group.interval
            item['lazy'] = FALLBACK_LAZY
            item['timeout'] = FALLBACK_TIMEOUT
            item['max-failed-times'] = FALLBACK_MAX_FAILED_TIMES
        if group.expression:
            expression = group.expression
            # MMWX filters explicit system outbounds as well as injected nodes.
            fixed_outbounds = [choice for choice in group.choices if choice in ('DIRECT', 'REJECT')]
            if fixed_outbounds:
                expression += '|^(' + '|'.join(fixed_outbounds) + ')$'
            item.update({'include-all-proxies': True, 'filter': expression})
        config['proxy-groups'].append(item)

    loon = [
        '# Loon 候选模板，节点注入与设备验证尚未完成。',
        '# 由 Personal/build.py 生成；规则与分组修改请编辑个人 INI。',
        '[General]', 'dns-server = system, 119.29.29.29, 223.5.5.5',
        'sni-sniffing = true', 'udp-fallback-mode = REJECT',
        'allow-wifi-access = false', 'interface-mode = auto', 'test-timeout = 5',
        '', '[Proxy]', '# 由支持 Loon 模板的生成器注入实际节点。', '', '[Proxy Group]',
    ]
    for group in groups:
        members = list(group.choices)
        if group.expression:
            members.append('NameRegexFilter = ' + group.expression)
        if group.kind == 'fallback':
            loon.append(group.name + ' = fallback, ' + ', '.join(members)
                        + ', url = ' + str(group.url) + ', interval = ' + str(group.interval))
        else:
            loon.append(group.name + ' = select, ' + ', '.join(members))

    # Keep CN at the end of remote rules rather than before service-specific ones.
    # The candidate's final precedence still needs verification on a Loon device.
    loon += ['', '[Rule]']
    remote_lines: list[str] = []
    for rule in rules:
        if rule.source.startswith('[]'):
            content = rule.source[2:]
            if content == 'FINAL':
                config['rules'].append('MATCH,' + rule.policy)
                loon.append('FINAL,' + rule.policy)
            elif content == 'GEOIP,CN':
                config['rules'].append(content + ',' + rule.policy + ',no-resolve')
                # ACL4SSR's ChinaIp list is CN CIDRs, retaining the final position.
                remote_lines.append('https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/ChinaIp.list'
                                    + ', policy=' + rule.policy + ', tag=personal-final-cn, enabled=true')
            elif content.startswith('DOMAIN-SUFFIX,'):
                config['rules'].append(content + ',' + rule.policy)
                loon.append(content + ',' + rule.policy)
            else:
                raise ValueError(f'Unsupported inline rule: {content}')
        else:
            key = Path(urlparse(rule.source).path).stem
            if key in config['rule-providers']:
                raise ValueError(f'Duplicate provider: {key}')
            config['rule-providers'][key] = {
                'type': 'http', 'behavior': 'classical', 'format': 'text',
                'url': rule.source, 'path': './ruleset/acl4-personal-' + key + '.list',
                'interval': 86400, 'proxy': '🚀 节点选择',
            }
            config['rules'].append('RULE-SET,' + key + ',' + rule.policy)
            remote_lines.append(rule.source + ', policy=' + rule.policy
                                + ', tag=personal-' + key + ', enabled=true')
    loon += ['', '[Remote Rule]'] + remote_lines
    header = ('# ACL4SSR Full NoAuto 个人扩展版 / CC-BY-SA-4.0\n'
              '# 由 Personal/build.py 生成；修改个人 INI 和 mihomo-base.yaml 后重新生成。\n'
              '# 不含节点，供妙妙屋 X 注入；除刷帖为回落组外全部手动选择。\n')
    (ROOT / 'acl4-full-personal__v3.yaml').write_text(
        header + yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=120), encoding='utf-8')
    (ROOT / 'acl4-full-personal.candidate.lcf').write_text('\n'.join(loon) + '\n', encoding='utf-8')
    print(json.dumps({'groups': len(groups),
                      'fallback': sum(1 for group in groups if group.kind == 'fallback'),
                      'providers': len(config['rule-providers']),
                      'rules': len(config['rules'])}, ensure_ascii=False))


if __name__ == '__main__':
    build()

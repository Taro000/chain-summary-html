#!/usr/bin/env python3
"""Build the outputs (docs/quality) of a fictional homework submission service (課題提出サービス),
to test shapes that the ride-hailing app does not have.

  uv run --with pyyaml python3 tests/make_homework_fixture.py

Writes to these two directories under skills/quality-summary-html/evals/:
  homework-service-full/files/docs/quality    stages 1 to 4
  homework-service-stage2/files/docs/quality  stages 1 and 2 only (no function proposals yet)
How it differs from the ride-hailing app: few items, a CUJ with two users, two EBPs, a deadline SLO,
a coverage check written per CUJ as the template does, and one FR missing from the report's coverage
table (the script should report it as an inconsistency).
"""
import pathlib
import shutil

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'skills' / 'quality-summary-html' / 'evals'
DAY1, DAY2, DAY3, DAY4 = '2026-09-01', '2026-09-03', '2026-09-08', '2026-09-12'


def common(i, title, agree=False):
    return {'id': i, 'title': title, 'status': 'draft', 'version': 1, 'basis': 'inferred', 'basis_note': None,
            'needs_agreement': agree, 'approver_candidates': ['プロダクトオーナー'] if agree else []}


def log(day, reason, change='作成'):
    return {'changelog': [{'version': 1, 'date': day, 'change': change, 'reason': reason}]}


CONTEXT = {
    'system': {
        'name': '課題提出サービス（homework-portal）',
        'boundary': '生徒と講師が使う Web アプリ（課題の配布、提出、採点、返却）、塾の事務が見る月次のレポート、それらを動かすサーバーとログ。保護者向けの画面と月謝の決済は除く。',
        'purpose': '生徒が期限までに課題を出し、講師が早く返せるようにする',
        'constraints': ['提出したファイルは外部のストレージに置く'],
        'data_producers': ['外部のストレージ（提出したファイル）'],
        'basis': 'stated',
    },
    'kgis': [{'id': 'KGI-01', 'name': '継続率', 'measure': '月末に在籍している生徒 ÷ 月初に在籍していた生徒', 'target': '95%', 'basis': 'stated'}],
    'outcomes': [
        {'id': 'OUT-01', 'statement': '期限までに課題を提出する生徒を増やす', 'verb': 'increase', 'kgis': ['KGI-01'], 'basis': 'stated'},
        {'id': 'OUT-02', 'statement': '返却の遅れについての問い合わせを減らす', 'verb': 'decrease', 'kgis': ['KGI-01'], 'basis': 'inferred'},
    ],
    'users': [
        {'id': 'USR-01', 'name': '生徒', 'category': 'primary', 'data_role': 'both', 'considered': True, 'exclusion_reason': None, 'basis': 'stated'},
        {'id': 'USR-02', 'name': '講師', 'category': 'primary', 'data_role': 'both', 'considered': True, 'exclusion_reason': None, 'basis': 'stated'},
        {'id': 'USR-03', 'name': '開発者', 'category': 'secondary-maintenance', 'data_role': 'consumer', 'considered': True, 'exclusion_reason': None,
         'basis': 'inferred', 'basis_note': '障害の調査をする人として推定'},
        {'id': 'USR-04', 'name': '塾の事務', 'category': 'indirect', 'data_role': 'consumer', 'considered': True, 'exclusion_reason': None, 'basis': 'stated'},
        {'id': 'USR-05', 'name': '保護者', 'category': 'indirect', 'data_role': 'consumer', 'considered': False,
         'exclusion_reason': '今期は保護者向けの画面を作らない（質問 2）', 'basis': 'confirmed'},
    ],
    'cujs': [
        {'id': 'CUJ-01', 'name': '課題の提出', 'users': ['USR-01'], 'user_goal': '期限までに、正しいファイルを迷わず提出する',
         'steps': ['課題を開く', 'ファイルを添付する', '提出する'], 'outcomes': ['OUT-01'], 'basis': 'stated'},
        {'id': 'CUJ-02', 'name': '採点と返却', 'users': ['USR-02'], 'user_goal': '提出を早く採点し、講評を付けて返す',
         'steps': ['提出を開く', '採点する', '返却する'], 'outcomes': ['OUT-02'], 'basis': 'stated'},
        {'id': 'CUJ-03', 'name': '提出の失敗の調査', 'users': ['USR-03'], 'user_goal': '提出できなかった原因を早く突き止めて直す',
         'steps': ['知らせを受ける', 'ログをたどる', '原因を直す'], 'outcomes': [], 'basis': 'inferred', 'basis_note': '手順は推定'},
        {'id': 'CUJ-04', 'name': '月次の提出状況の確認', 'users': ['USR-04', 'USR-02'], 'user_goal': '未提出の生徒を月ごとに確かめ、声をかける',
         'steps': ['レポートを開く', '未提出の生徒を確かめる'], 'outcomes': ['OUT-01'], 'basis': 'stated'},
    ],
    'hints': [{'statement': '生徒の個人情報を扱う', 'kind': 'law', 'source': '入力の要望書'}],
    'operational_facts': [{'fact': '提出は締め切り前の 24 時間に集まる', 'source': '入力の要望書'}],
}


def qiu(i, title, user, cuj, outs, char, statement, failure, num, den, narrowed, kpi, observable=True, status='draft'):
    d = common(i, title)
    d['status'] = status
    d.update({'user': user, 'cuj': cuj, 'outcomes': outs, 'need': statement,
              'context_of_use': {'device': 'スマートフォンのブラウザ', 'network': None, 'user_type': None, 'task': title, 'environment': None, 'other': None},
              'characteristic': char, 'statement': statement, 'failure_scenario': failure,
              'measure': {'numerator': num, 'denominator': den, 'narrowed_to': narrowed, 'denominator_needed_only': None,
                          'contribution': None, 'observable': observable, 'compared_with': None, 'scale': 'ratio'},
              'kpi': kpi, 'target': None, 'target_status': 'undecided'})
    d.update(log(DAY1, '第 1 段階の下書き'))
    return d


QIUS = [
    qiu('QIU-01', '期限までに提出が終わる', 'USR-01', 'CUJ-01', ['OUT-01'], 'effectiveness', '生徒はスマートフォンからでも、期限までに課題の提出を終えられる。',
        '締め切り直前に提出が失敗し、期限に間に合わない。', '提出が完了した課題', '提出を始めた課題', 'スマートフォンのブラウザ、締め切り前の 24 時間', 'KPI-01'),
    qiu('QIU-02', '提出したことを確かめられる', 'USR-01', 'CUJ-01', [], 'satisfaction > trust', '生徒は、提出した課題が講師に届いたことをその場で確かめられる。',
        '受領の表示がなく、生徒が同じ課題を何度も出し直す。', '受領の表示を見た提出', '完了した提出', 'すべての提出', None, observable=False),
    qiu('QIU-03', '3 日以内に返る', 'USR-02', 'CUJ-02', ['OUT-02'], 'efficiency', '講師は、提出から 3 日以内に採点して返却できる。',
        '採点の画面が重く、返却が週をまたぐ。', '3 日以内に返却した提出', '返却した提出', '講師が担当する通常の課題', 'KPI-02'),
    qiu('QIU-04', '失敗の原因を 30 分で特定する', 'USR-03', 'CUJ-03', [], 'efficiency', '開発者は、提出の失敗の原因を知らせから 30 分以内に特定できる。',
        'ログがつながらず、原因の特定に半日かかる。', '30 分以内に原因を特定した失敗', '調査した失敗', '本番の失敗の知らせ', None),
    qiu('QIU-05', '月次の数字が提出と合う', 'USR-04', 'CUJ-04', ['OUT-01'], 'freedom from risk > economic risk mitigation',
        '塾の事務は、月次のレポートの件数が実際の提出の記録と一致していると信じて使える。', '未提出の生徒を取り違え、提出した生徒に催促する。',
        '提出の記録と一致した月次の件数', '月次の件数', '月末の締め', None),
    qiu('QIU-06', '保護者に提出を知らせる', 'USR-05', 'CUJ-01', [], 'effectiveness', '保護者は提出を知れる。', '保護者が提出を知らない。',
        '知らせた提出', '提出', '—', None, status='retired'),
]


def kpi(i, title, out, num, den, overlaps):
    d = common(i, title)
    d.update({'outcome': out, 'numerator': num, 'denominator': den, 'counted_over': 'すべての生徒と端末', 'overlaps_with': overlaps,
              'overlap_note': None, 'target': None, 'target_status': 'undecided'})
    d.update(log(DAY1, '第 1 段階の下書き'))
    return d


KPIS = [kpi('KPI-01', '提出完了率', 'OUT-01', '提出が完了した課題', '提出を始めた課題', ['QIU-01']),
        kpi('KPI-02', '3 日以内の返却率', 'OUT-02', '3 日以内に返却した提出', '返却した提出', ['QIU-03'])]


def fr(i, title, origin, cuj, step, traces, statement, ac, existing=False, proposal=None, status='draft'):
    d = common(i, title)
    d['status'] = status
    d.update({'statement': statement, 'origin': origin, 'cuj': cuj, 'cuj_step': step, 'traces_to': traces, 'proposal': proposal,
              'existing': existing, 'extends': None, 'interface': ['画面: 生徒の Web アプリ'], 'acceptance_criteria': ac, 'quality_hints': []})
    d.update(log(DAY2, '第 2 段階の下書き'))
    return d


FRS = [
    fr('FR-01', '課題の提出', 'cuj-step', 'CUJ-01', '提出する', ['QIU-01', 'KPI-01'], 'システムは、生徒が添付したファイルを課題への提出として受け付ける。',
       ['期限までに提出すると、提出の記録を作り「提出しました」と示す。', '期限を過ぎた提出は、遅れの印を付けて受け付ける。'], existing=True),
    fr('FR-02', '受領の表示', 'quality-in-use', 'CUJ-01', '提出する', ['QIU-02'], 'システムは、提出を受け付けると、受領の番号と時刻を生徒に示す。',
       ['提出の直後に受領の番号と時刻を示す。', '提出の履歴から、過去の受領を開ける。']),
    fr('FR-03', '採点と返却', 'cuj-step', 'CUJ-02', '返却する', ['QIU-03', 'KPI-02'], 'システムは、講師が点と講評を付けた提出を生徒に返却する。',
       ['返却すると、生徒の画面に点と講評を示す。']),
    fr('FR-04', 'トレース ID', 'quality-in-use', 'CUJ-03', 'ログをたどる', ['QIU-04'], 'システムは、提出の要求ごとにトレース ID を付け、すべてのログに残す。',
       ['提出の要求が通るすべての部品のログに、同じトレース ID が出る。']),
    fr('FR-05', '夜間の提出状況レポート', 'cuj-step', 'CUJ-04', 'レポートを開く', ['QIU-05'], 'システムは、毎晩、前日までの提出状況をまとめたレポートを作る。',
       ['毎朝 6:00 までに、生徒ごとの提出と未提出の件数をレポートに示す。']),
    fr('FR-06', '下書きの自動保存', 'proposal', 'CUJ-01', 'ファイルを添付する', ['QIU-01'], 'システムは、添付したファイルを提出の前に下書きとして保存する。',
       ['通信が切れても、添付したファイルが下書きに残る。'], proposal='FRP-01'),
    fr('FR-07', '一括ダウンロード', 'cuj-step', 'CUJ-02', '提出を開く', ['QIU-03'], 'システムは、提出をまとめてダウンロードさせる。', ['—'], status='retired'),
    fr('FR-08', '返却の通知', 'cuj-step', 'CUJ-02', '返却する', ['QIU-03'], 'システムは、返却したことを生徒に通知する。', ['返却すると、生徒に通知が届く。']),
]


def frp(i, title, status, origin, statement, resolution):
    return {'id': i, 'title': title, 'status': status, 'version': 1, 'basis': 'inferred', 'basis_note': None, 'needs_agreement': False,
            'approver_candidates': [], 'proposed_by': 'functional-requirements-to-product-quality', 'origin': origin, 'changes': None,
            'reason': statement, 'suggested_statement': statement, 'affects': [], 'placeholders': [], 'resolution': resolution,
            'changelog': [{'version': 1, 'date': DAY3, 'change': '提案', 'reason': '第 3 段階'}]}


FRPS = [frp('FRP-01', '下書きの自動保存', 'accepted', ['QR-06'], '添付したファイルを下書きとして保存する', 'FR-06 として受け入れた'),
        frp('FRP-02', '提出の自動の再送', 'rejected', ['QR-01'], '失敗した提出を自動で送り直す', 'FR-06 の下書きで足りるため受け入れない')]


def qr(i, title, model, layer, char, applies, traces, statement, failure, score, handling, reason=None, internal=(), entry=None, status='draft'):
    d = common(i, title, agree=True)
    d['status'] = status
    d.update({'model': model, 'layer': layer, 'characteristic': char, 'statement': statement, 'applies_to': applies, 'traces_to': traces,
              'entry_point': entry, 'stakeholders': ['USR-01'], 'failure_scenario': failure,
              'score': {'impact': score[0], 'likelihood': score[1]} if score else None, 'handling': handling, 'handling_reason': reason,
              'implies_internal': list(internal), 'conflicts': [], 'stated_numbers': [], 'placeholders': []})
    d.update(log(DAY3, '第 3 段階の下書き'))
    return d


QRS = [
    qr('QR-01', '提出の可用性', 'product', 'external', 'reliability > availability', ['FR-01'], ['QIU-01'],
       '生徒は締め切り前の混雑時にも提出できる。', '締め切り直前に提出の画面がエラーになる。', (5, 3), 'emphasized', internal=['QR-05']),
    qr('QR-02', '提出の応答の速さ', 'product', 'external', 'performance efficiency > time behaviour', ['FR-01'], ['QIU-01'],
       '提出の確定が、生徒を待たせない速さで終わる。', '提出の確定に時間がかかり、生徒が画面を閉じる。', (3, 3), 'minimum-line'),
    qr('QR-03', '受領の表示の正しさ', 'product', 'external', 'functional suitability > functional correctness', ['FR-02'], ['QIU-02'],
       '受領の表示は、実際に保存した提出とだけ一致する。', '保存に失敗したのに受領を示す。', (4, 2), 'emphasized', internal=['QR-05']),
    qr('QR-04', '返却の通知の分かりやすさ', 'product', 'external', 'usability > operability', ['FR-08'], ['QIU-03'],
       '生徒は返却の通知から講評にすぐたどり着ける。', '通知から講評が開けず、生徒が講評を読まない。', (2, 2), 'excluded',
       reason='今期は対象外: 通知の文面は講師が自分で書くため'),
    qr('QR-05', '提出の処理の自動テスト', 'product', 'internal', 'maintainability > testability', ['FR-01', 'FR-02'], ['QIU-01', 'QIU-02'],
       '提出と受領の処理は、自動テストで振る舞いを確かめられる。', None, None, 'minimum-line'),
    qr('QR-06', 'ストレージの障害への耐性', 'product', 'external', 'reliability > fault tolerance', ['FR-01', 'FR-06'], ['QIU-01'],
       '外部のストレージが一時的に失敗しても、添付したファイルを失わない。', 'ストレージの失敗で添付が消え、生徒が作り直す。', (4, 2), 'emphasized'),
    qr('QR-07', '提出の記録の完全性', 'data', 'data-inherent', 'completeness', ['FR-01', 'FR-05'], ['QIU-05'],
       '提出の記録に、生徒、課題、時刻の欠けがない。', '時刻の欠けた記録がレポートから漏れる。', (4, 3), 'emphasized'),
    qr('QR-08', 'レポートの最新性', 'data', 'data-inherent', 'currentness', ['FR-05'], ['QIU-05'],
       '月次のレポートは、前日までの提出を毎朝反映している。', '夜間の処理が遅れ、古い未提出の一覧で催促する。', (3, 2), 'minimum-line'),
    qr('QR-09', '生徒の個人情報の機密性', 'product', 'external', 'security > confidentiality', ['FR-01', 'FR-03'], [],
       '生徒の氏名と提出物は、担当の講師と本人のほかに見えない。', '他の生徒の提出物が見える。', (5, 2), 'emphasized',
       reason='法令から来る要求なので点に関わらず残す。', entry={'type': 'law', 'source': '個人情報の保護に関する法律。生徒の氏名と提出物を扱う', 'brought_by': '開発の責任者'}),
    qr('QR-10', '失敗をたどれること', 'product', 'external', 'maintainability > analysability', ['FR-04'], ['QIU-04'],
       '開発者は、提出の失敗を 1 件ずつ部品をまたいでたどれる。', 'ログがつながらず原因を特定できない。', (3, 3), 'minimum-line'),
    qr('QR-11', '古い要求', 'product', 'external', 'usability > learnability', ['FR-01'], ['QIU-01'], '—', '—', (1, 1), 'excluded', status='retired'),
    qr('QR-12', '採点の正確さ', 'product', 'external', 'functional suitability > functional correctness', ['FR-03'], ['QIU-03'],
       '返却した点は、講師が付けた点と一致する。', '点の保存を誤り、違う点が返る。', (4, 2), 'emphasized'),
    qr('QR-13', '提出の復元', 'data', 'data-system-dependent', 'recoverability', ['FR-01'], [],
       '提出から 1 年は、消えた提出を復元できる。', 'ストレージの障害で提出が消え、成績の根拠を失う。', (3, 1), 'minimum-line',
       reason='開発方針から来る要求なので点に関わらず残す。', entry={'type': 'policy', 'source': '開発方針: 提出は 1 年間保管する', 'brought_by': 'プロダクトオーナー'}),
]


def nfr(i, title, frm, kind, cuj, statement, slo=None, gate=None, audit=None, monitor=None):
    d = common(i, title, agree=True)
    d.update({'from': frm, 'kind': kind, 'cuj': cuj, 'statement': statement,
              'conditions': {'workload': '締め切り前の 24 時間に集中', 'users': '生徒と講師。テスト用アカウントを除く', 'transactions': '提出'},
              'slo': slo, 'gate': gate, 'audit': audit, 'monitor': monitor})
    d.update(log(DAY4, '第 4 段階の下書き'))
    return d


ALERTS = [{'notify': 'page', 'long_window': '1h', 'short_window': '5m', 'burn_rate': 14.4, 'budget_spent_at_alert': '2.1%', 'condition': None},
          {'notify': 'ticket', 'long_window': '3d', 'short_window': '6h', 'burn_rate': 1, 'budget_spent_at_alert': '10.7%', 'condition': None}]
NFRS = [
    nfr('NFR-01', '提出の可用性の SLO', ['QR-01', 'QR-06'], 'slo', 'CUJ-01', '直近 28 日で、有効な提出の要求の 99.5% が、サーバーのエラーなしに応える。',
        slo={'sli': 'SLI-01', 'target': '99.5%', 'target_status': 'provisional', 'target_rationale': '運用の実績がないので保守的にした',
             'window': '28-day rolling', 'error_budget': '有効な提出の要求の 0.5% までがエラーになってよい',
             'error_budget_volume': '28 日の提出の件数 × 0.005', 'policy': 'EBP-01', 'alerts': ALERTS}),
    nfr('NFR-02', '夜間レポートの締め切りの SLO', ['QR-08'], 'slo', 'CUJ-04', '直近 28 日で、夜間レポートの 99% が毎朝 6:00 までに終わる。',
        slo={'sli': 'SLI-02', 'target': '99%', 'target_status': 'provisional', 'target_rationale': '提案', 'window': '28-day rolling',
             'error_budget': '28 日のうち 1% までの夜は 6:00 を過ぎてよい', 'error_budget_volume': '28 日で 0.28 回（1 回でも遅れると使い切る）',
             'policy': 'EBP-02', 'bad_run_budget_share': '1 回の遅れでバジェットの 357%', 'progress_alert': 'NFR-05（5:30 に終わっていなければ知らせる）',
             'after_miss': 'ticket'}),
    nfr('NFR-03', '受領の表示の E2E テスト', ['QR-03'], 'gate', 'CUJ-01', '提出から受領の表示までを E2E テストで確かめ、失敗したら配備を止める。',
        gate={'where': 'CI', 'check': '提出から受領の表示までの E2E テスト', 'threshold': '失敗 0 件'}),
    nfr('NFR-04', '提出の処理のテストの網羅', ['QR-05'], 'gate', 'CUJ-01', '提出と受領の処理の分岐を、自動テストで 80% 以上網羅する。',
        gate={'where': 'definition-of-done', 'check': '提出と受領の処理の分岐の網羅', 'threshold': '80%'}),
    nfr('NFR-05', '夜間レポートの進み具合', ['QR-08'], 'monitor', 'CUJ-04', '夜間レポートが 5:30 に終わっていなければ開発者に知らせる。',
        monitor={'signal': 'レポートの処理の終了の記録', 'threshold': '5:30 に終わっていない', 'notifies': '開発者（チャット）'}),
    nfr('NFR-06', '提出の応答の遅さの監視', ['QR-02'], 'monitor', 'CUJ-01', '提出の確定の 95 パーセンタイルが 3 秒を超えたら知らせる。',
        monitor={'signal': '提出の確定の応答時間', 'threshold': '95 パーセンタイルが 3 秒を超えて 1 時間続く', 'notifies': '開発者（チケット）'}),
    nfr('NFR-07', '提出の記録の欠けの監視', ['QR-07'], 'monitor', 'CUJ-04', '時刻か生徒の欠けた提出の記録が見つかったら、その日のうちに知らせる。',
        monitor={'signal': '毎晩の記録の確かめ', 'threshold': '欠け 1 件', 'notifies': '開発者と塾の事務'}),
    nfr('NFR-08', '個人情報の扱いの監査', ['QR-09'], 'audit', None, '半年ごとに、提出物を見られる権限を棚卸しする。',
        audit={'mechanism': 'アクセス権の棚卸し', 'criterion': '不要な権限 0 件', 'cadence_or_deadline': '半年ごと'}),
    nfr('NFR-09', 'トレース ID の完成の定義', ['QR-10'], 'gate', 'CUJ-03', '提出の経路の部品は、トレース ID をログに出すまで完成としない。',
        gate={'where': 'definition-of-done', 'check': 'ログにトレース ID が出ること', 'threshold': '全部品'}),
    nfr('NFR-10', '採点の二重確認', ['QR-12'], 'gate', 'CUJ-02', '採点の保存を変える変更は、リリース前に点の一致を確かめる。',
        gate={'where': 'release-check', 'check': '保存した点と入力した点の一致', 'threshold': '不一致 0 件'}),
    nfr('NFR-11', '復元の訓練', ['QR-13'], 'audit', None, '年に一度、消した提出を復元する訓練をする。',
        audit={'mechanism': '復元の訓練', 'criterion': '1 時間以内に復元できる', 'cadence_or_deadline': '毎年 3 月'}),
]


def sli(i, title, refs, func, elements, method):
    return {'id': i, 'title': title, 'status': 'draft', 'version': 1, 'basis': 'inferred', 'basis_note': None, 'needs_agreement': True,
            'approver_candidates': ['開発の責任者'], 'function': func, 'refs': refs, 'reshaped': None, 'target_entity': '本番のサーバー',
            'purpose': title, 'unit_event': '要求', 'method': method, 'elements': elements, 'scale': 'ratio', 'applicability': '本番',
            'lifecycle': '本番で測る', 'blind_spots': 'ブラウザの中の失敗は見えない',
            'changelog': [{'version': 1, 'date': DAY4, 'change': '作成', 'reason': '第 4 段階の下書き'}]}


SLIS = [
    sli('SLI-01', '提出の可用性', ['QR-01', 'NFR-01'], 'OK ÷ VALID',
        {'VALID': {'definition': 'ログインした生徒からの提出の要求', 'inputs': 'アクセスログ', 'unit': 'requests', 'counting_rule': '1 分ごとに合計'},
         'OK': {'definition': 'VALID のうち、status が 5xx でない要求', 'inputs': 'VALID と同じ', 'unit': 'requests', 'counting_rule': 'VALID と同じ'}},
        'アクセスログ法'),
    sli('SLI-02', '夜間レポートの締め切り', ['QR-08', 'NFR-02'], 'ON_TIME ÷ RUNS',
        {'RUNS': {'definition': '予定した夜間レポートの実行', 'inputs': 'ジョブの記録', 'unit': 'runs', 'counting_rule': '1 晩 1 回'},
         'ON_TIME': {'definition': 'RUNS のうち、6:00 までに終わったもの', 'inputs': 'RUNS と同じ', 'unit': 'runs', 'counting_rule': 'RUNS と同じ'}},
        'ジョブの記録法'),
]
EBPS = [
    dict(common('EBP-01', '提出の SLO のエラーバジェット方針', agree=True),
         applies_to=['NFR-01'],
         rules=[{'when': '残りのバジェットが 50% を下回った', 'action': '次のスプリントは信頼性の作業を先にする'},
                {'when': 'バジェットを使い切った', 'action': 'ウィンドウの残りは修正だけを出す'},
                {'when': '締め切り前の 24 時間', 'action': '提出に関わる配備をしない'}], **log(DAY4, '第 4 段階の下書き')),
    dict(common('EBP-02', 'データの SLO のエラーバジェット方針', agree=True),
         applies_to=['NFR-02'],
         rules=[{'when': 'レポートが 6:00 に間に合わなかった', 'action': '原因を直す作業と、その朝の催促の取り消しを起票する'},
                {'when': '同じ月に 2 回遅れた', 'action': '夜間の処理の見直しを次のスプリントで先にする'}], **log(DAY4, '第 4 段階の下書き')),
]

REPORT1 = '''# 利用時の品質と KPI: 課題提出サービス

更新: 2026-09-01

## 利用時の品質要求

### 対象にしない

| CUJ | 特性 | 理由 |
|---|---|---|
| CUJ-01〜03 | 満足性 > 快感性 | 入力にこのニーズがなく、成果を損なう失敗のシナリオも書けない。 |
| CUJ-04 | 利用状況網羅性 > 柔軟性 | 事務の使い方は月末の確認の一つだけ。 |
'''
REPORT2_FULL = '''# 機能要件: 課題提出サービス

更新: 2026-09-08

## 利用時の品質要求の対応

| QIU | どう対応するか | FR | 第 3 段階への品質のヒント |
|---|---|---|---|
| QIU-01 期限までに提出が終わる | 既存の提出と下書き | FR-01、FR-06 | 有効性 (QIU-01) - 混雑時も提出できる |
| QIU-02 提出したことを確かめられる | 新しい機能 | FR-02 | |
| QIU-03 3 日以内に返る | 既存の採点 | FR-03 | |
| QIU-04 失敗の原因を 30 分で特定する | 新しい機能 | FR-04 | |
| QIU-05 月次の数字が提出と合う | 既存のレポート | FR-05 | |

## 検討して加えなかった機能

| 候補 | 対象 | 理由 |
|---|---|---|
| 提出の期限を自動で延ばす | QIU-01 | 期限は講師が決める。 |
| 採点の下書きを共有する | QIU-03 | 講師は一人で採点する。 |
'''
REPORT2_STAGE2 = REPORT2_FULL.replace('FR-01、FR-06', 'FR-01').replace('既存の提出と下書き', '既存の提出')
REPORT3 = '''# 製品の品質とデータの品質: 課題提出サービス

更新: 2026-09-08

## 網羅の確認

### CUJ-01 課題の提出

| モデル | 特性 > 副特性 | 候補（QR）または対象にしない理由 |
|---|---|---|
| 製品 | 信頼性 > 可用性 | QR-01 |
| データ | 完全性 | QR-07 |

主なデータ: 提出の記録、提出したファイル、採点と講評、月次の提出状況のレポート。

データを作る人: 生徒（提出したファイル）、講師（点と講評）、外部のストレージ（保存したファイル）。

## 外部品質から導いた内部品質

| 外部の QR | 内部の QR | どう支えるか |
|---|---|---|
| QR-01、QR-03 | QR-05 | 提出と受領の処理を自動テストで確かめるので、壊れた変更を本番に出さない。 |
'''
REPORT4 = '''# 非機能要件、SLI、SLO: 課題提出サービス

更新: 2026-09-12

## 割り当て

| QR | 扱い | 品質を支える機能 | 非機能要件 | 種類 | 範囲外 |
|---|---|---|---|---|---|
| QR-01 提出の可用性 | 重視 | なし | NFR-01 | SLO | |
| QR-04 返却の通知の分かりやすさ | 今期は対象外 | なし | | | 通知の文面は講師が書く |
| QR-13 提出の復元 | 最低限守る線 | なし | NFR-11 | 監査 | ストレージの事業者の障害そのものは範囲外 |
'''


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000), encoding='utf-8')


def write(dest, stage):
    if dest.exists():
        shutil.rmtree(dest)
    dump(dest / 'context.yaml', CONTEXT)
    for d in QIUS:
        dump(dest / 'qiu' / ('%s.yaml' % d['id']), d)
    for d in KPIS:
        dump(dest / 'kpi' / ('%s.yaml' % d['id']), d)
    for d in FRS:
        if stage < 3 and d['id'] == 'FR-06':
            continue
        dump(dest / 'fr' / ('%s.yaml' % d['id']), d)
    (dest / '1-quality-in-use.md').write_text(REPORT1, encoding='utf-8')
    (dest / '2-functional-requirements.md').write_text(REPORT2_FULL if stage >= 3 else REPORT2_STAGE2, encoding='utf-8')
    if stage < 3:
        return
    for d in FRPS:
        dump(dest / 'frp' / ('%s.yaml' % d['id']), d)
    for d in QRS:
        dump(dest / 'qr' / ('%s.yaml' % d['id']), d)
    (dest / '3-product-quality.md').write_text(REPORT3, encoding='utf-8')
    for d in NFRS:
        dump(dest / 'nfr' / ('%s.yaml' % d['id']), d)
    for d in SLIS:
        dump(dest / 'sli' / ('%s.yaml' % d['id']), d)
    for d in EBPS:
        dump(dest / 'ebp' / ('%s.yaml' % d['id']), d)
    (dest / '4-nfr-slo.md').write_text(REPORT4, encoding='utf-8')


if __name__ == '__main__':
    write(ROOT / 'homework-service-full' / 'files' / 'docs' / 'quality', 4)
    write(ROOT / 'homework-service-stage2' / 'files' / 'docs' / 'quality', 2)
    print('書き出し:', ROOT / 'homework-service-full', ROOT / 'homework-service-stage2')

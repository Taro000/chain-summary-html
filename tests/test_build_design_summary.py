"""Tests for design-summary-html's build script. They need PyYAML; run them from the repository root like this:

  uv run --with pyyaml python3 -m unittest discover -s tests -v

The fixture is a small, made-up design (one driver of each kind that matters, two decisions, two elements, one
interface, one data entity) written into a temporary directory, so the tests do not depend on any other repository.
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills' / 'design-summary-html' / 'scripts' / 'build_design_summary.py'

ITEMS = {
    'drv/DRV-01.yaml': """
        id: DRV-01
        title: 注文をすぐ確定する
        status: draft
        kind: quality
        statement: 注文を待たせずに確定する
        sources: [QR-02, NFR-01]
        scenario: {source: 買い手, stimulus: 注文を送る, artifact: FR-01, environment: セールの山, response: 確定を示す, measure: 99% が 1.5 秒以内}
        priority: {business: high, business_reason: QR-02 が重視, difficulty: high, difficulty_reason: 決済の待ちが入る, rank: 2}
        primary: true
        conflicts: [{with: DRV-02, note: 審査が待ちを足す（FND-03）}]
    """,
    'drv/DRV-02.yaml': """
        id: DRV-02
        title: 決済は外部に任せる
        status: draft
        kind: constraint
        statement: カード番号はサーバーに届かない
        sources: [TC-01]
        negotiable: false
        priority: {business: high, business_reason: 交渉できない制約, difficulty: medium, difficulty_reason: 画面に部品を埋める, rank: 1}
        primary: true
        conflicts: [{with: DRV-01, note: 審査が待ちを足す}]
    """,
    'drv/DRV-03.yaml': """
        id: DRV-03
        title: 古い制約
        status: retired
        kind: constraint
        statement: 廃止した
    """,
    'dec/DEC-01.yaml': """
        id: DEC-01
        title: 一つのサーバーにする
        status: draft
        stage: architecture
        question: システムをどう分けるか
        addresses: [DRV-02, DRV-01]
        options:
          - {name: 一つのサーバー, effect: 一人で動かせる, cost: 一つが止まると全体が止まる}
          - {name: 機能ごとのサービス, effect: 別々に増やせる, cost: 運用が増える}
        chosen: 一つのサーバー
        rationale: 一人で動かせる案だけが DRV-02 を満たす。前の版は二つに分けていた
        rejected: [{option: 機能ごとのサービス, reason: 一人で動かせない}]
        gains: [配備が一つで済む]
        costs: [一つの障害の単位になる]
        sensitive_points: [インスタンスの数]
        trade_offs: [{with: DRV-01, note: 増やす余地が減る}]
        assumptions: [利用者は少ない]
        depends_on: []
        parameters: [{name: 最大のインスタンス, value: '1', basis: 利用者が少ない}]
        debt: {what: 一つの障害の単位, why_accepted: 規模が小さい, repay_when: 利用者が増えたとき}
        deferred: false
    """,
    'dec/DEC-02.yaml': """
        id: DEC-02
        title: エラーの形
        status: draft
        stage: high-level-design
        question: エラーをどの形で返すか
        addresses: [IFC-01]
        options: [{name: 問題の詳細, effect: 標準, cost: なし}]
        chosen: 問題の詳細
        rejected: []
        parameters: [{name: limit, value: 既定 20, basis: 提案}]
    """,
    'dec/DEC-03.yaml': """
        id: DEC-03
        title: 詳細設計の決定
        status: draft
        stage: detailed-design
        question: 第 4 段階の問い
    """,
    'elm/ELM-01.yaml': """
        id: ELM-01
        title: サーバー
        status: draft
        kind: component
        name: サーバー
        responsibility: 注文を受けて確定する
        functions: [FR-01, FR-02, FR-03, FR-05]
        drivers: [DRV-01]
        team: TEAM-01
        as_is: new
    """,
    'elm/ELM-02.yaml': """
        id: ELM-02
        title: データベース
        status: draft
        kind: data-store
        name: データベース
        responsibility: 注文を持つ
        functions: []
        drivers: []
        team: TEAM-01
        as_is: new
    """,
    'ifc/IFC-01.yaml': """
        id: IFC-01
        title: 注文の API
        status: draft
        kind: http
        name: 注文の API
        provider: ELM-01
        consumers: [ELM-02]
        functions: [FR-01]
        operations: [{name: POST /v1/orders, does: 注文を確定する}]
        errors:
          - {case: 'POST /v1/orders: カードが通らない', signal: 402 CARD_DECLINED, caller_does: 断りを示す}
          - {case: '共通: ログインしていない', signal: 401 UNAUTHENTICATED, caller_does: ログインの画面へ}
        spec: ifc/specs/orders.openapi.yaml
    """,
    'dat/DAT-01.yaml': """
        id: DAT-01
        title: 注文
        status: draft
        entity: 注文
        owner: ELM-01
        store: ELM-02
        consistency: 一つのトランザクションで書く
        retention: null
        classification: personal（買い手の住所）
    """,
    'design-context.yaml': """
        technology_constraints:
          - {id: TC-01, statement: カードは決済サービスの部品で受ける, kind: external-service, source: 入力, basis: stated}
        project_constraints:
          - {id: PC-01, kind: team, statement: 一人, source: 入力, basis: confirmed}
        teams:
          - {id: TEAM-01, name: 開発者, owns: すべて, basis: stated}
        stakeholders: []
    """,
}

# The reports restate some items; this one is stale (its ranking table lists DRV-09, which no item has)
REPORT1 = """
    # 設計を動かす要求: お店

    ## 順位表

    | 順位 | DRV | 事業の優先度 | 理由 | 設計上の難しさ | 理由 | 主 |
    |---|---|---|---|---|---|---|
    | 1 | DRV-02 | 高 | x | 中 | x | はい |
    | 2 | DRV-09 | 高 | x | 高 | x | はい |

    ## 関心事の一覧

    | 入力の項目 | 種類 | 誰の関心事 | なったもの |
    |---|---|---|---|
    | QR-02 | 品質 | 買い手 | DRV-01 |

    ## 実現できるか

    | 主な要求 | 判定 |
    |---|---|
    | DRV-01 | できる |
"""

REPORT2 = """
    # アーキテクチャ: お店

    ## 設計の決定

    | DEC | 問い | 選んだ案 | 対象 | 退けた案 | 根拠 |
    |---|---|---|---|---|---|
    | DEC-01 | 報告書の古い問い | 報告書の古い案 | DRV-01 | x | 推定 |

    ### DEC-01 全体の構造

    | 要求（順位） | 一つのサーバー | 機能ごと |
    |---|---|---|
    | DRV-02（1） | 満たす | 満たさない |

    ## ビュー

    ### 外部との関係

    ```mermaid
    flowchart LR
      a["ELM-01"] --> b["ELM-02"]
    ```
"""


def write_fixture(root: pathlib.Path, reports=True) -> pathlib.Path:
    d = root / 'docs' / 'design'
    for name, body in ITEMS.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip(), encoding='utf-8')
    if reports:
        (d / '1-architecture-drivers.md').write_text(textwrap.dedent(REPORT1).lstrip(), encoding='utf-8')
        (d / '2-architecture.md').write_text(textwrap.dedent(REPORT2).lstrip(), encoding='utf-8')
    return d


def build(d: pathlib.Path, *extra):
    out = d / 'summary.html'
    r = subprocess.run([sys.executable, str(SCRIPT), str(d), '--out', str(out)] + list(extra),
                       capture_output=True, text=True, timeout=120)
    page = out.read_text(encoding='utf-8') if out.exists() else ''
    return r, page


def toggle(page, tid):
    m = re.search(r'<details class="tbl" id="%s"[^>]*>.*?</details>(?=<details class="tbl"|</section>|\s*</main>)' % tid, page, re.S)
    return m.group(0) if m else ''


class YamlFirst(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = write_fixture(pathlib.Path(cls.tmp.name))
        cls.r, cls.page = build(cls.d)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_written(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        self.assertIn('<title>お店の設計</title>', self.page)

    def test_ranking_follows_the_yaml(self):
        rank = toggle(self.page, 't-rank')
        self.assertLess(rank.index('rank-DRV-02'), rank.index('rank-DRV-01'))
        self.assertNotIn('DRV-09', rank)
        self.assertNotIn('DRV-03', rank)                    # retired

    def test_stale_report_is_reported(self):
        self.assertIn('順位表: 報告書にあって YAML にない DRV-09', self.r.stdout)
        self.assertIn('順位表: YAML にあって報告書にない DRV-01', self.r.stdout)
        self.assertIn('食い違い:', toggle(self.page, 't-notes'))

    def test_decision_from_the_yaml_not_the_report(self):
        dec = toggle(self.page, 't-dec')
        self.assertIn('システムをどう分けるか', dec)
        self.assertNotIn('報告書の古い問い', self.page)
        card = toggle(self.page, 't-decd')
        self.assertIn('class="is-chosen"', card)
        self.assertIn('一人で動かせない', card)            # the rejected option's reason
        self.assertIn('配備が一つで済む', card)             # gains
        self.assertNotIn('満たさない', card)                # the report's comparison table is not used
        self.assertNotIn('前の版', card)                    # revision notes are removed from YAML text too

    def test_debt_values_and_stages(self):
        self.assertIn('一つの障害の単位', toggle(self.page, 't-debt'))
        self.assertIn('最大のインスタンス', toggle(self.page, 't-values2'))
        self.assertIn('既定 20', toggle(self.page, 't-values3'))
        self.assertIn('エラーの形', toggle(self.page, 't-dec3'))
        self.assertNotIn('第 4 段階の問い', self.page)       # detailed-design decisions are not on this page

    def test_conflict_shown_once_per_pair(self):
        conf = toggle(self.page, 't-conflict')
        self.assertIn('1 組', conf)
        self.assertNotIn('FND-03', conf)

    def test_interfaces_errors_and_data(self):
        self.assertIn('orders.openapi.yaml', toggle(self.page, 't-ifc'))
        err = toggle(self.page, 't-err')
        self.assertIn('POST /v1/orders', err)
        self.assertIn('402 CARD_DECLINED', err)
        self.assertIn('共通', err)
        data = toggle(self.page, 't-data')
        self.assertIn('個人情報（買い手の住所）', data)
        self.assertIn('用語集にない値: なし', self.r.stdout)

    def test_id_ranges(self):
        text = re.sub(r'<[^>]+>', '', toggle(self.page, 't-elm'))
        self.assertIn('FR-01〜03、05', text)

    def test_report_only_sections_and_diagrams(self):
        self.assertIn('関心事の一覧', self.page)
        self.assertIn('実現できるか', self.page)
        self.assertIn('class="mmd"', toggle(self.page, 't-views'))

    def test_premises_from_design_context(self):
        pre = toggle(self.page, 't-premise')
        self.assertIn('技術制約: 外部サービス', pre)
        self.assertIn('体制', pre)
        self.assertIn('確認済み', pre)


class WithoutReports(unittest.TestCase):
    def test_builds_from_the_yaml_alone(self):
        with tempfile.TemporaryDirectory() as t:
            d = write_fixture(pathlib.Path(t), reports=False)
            r, page = build(d)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('1-architecture-drivers.md がない', r.stdout)
            self.assertIn('id="t-rank"', page)
            self.assertIn('id="t-decd"', page)
            self.assertNotIn('id="t-views"', page)

    def test_nothing_to_build(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / 'docs' / 'design'
            d.mkdir(parents=True)
            r, _ = build(d)
            self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()

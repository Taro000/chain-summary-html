#!/usr/bin/env python3
"""Build the design outputs (docs/design) of the fictional homework submission service (課題提出サービス) for
design-summary-html's evals, in the layout of req-to-design 0.3.0, on top of the quality outputs in
quality-summary-html's evals.

  uv run --with pyyaml python3 tests/make_homework_design_fixture.py [REQ_TO_DESIGN]

Writes to these directories under skills/design-summary-html/evals/:
  homework-service-full/files/docs      stages 1, 2, 2b and 3 of the design, in Japanese, and docs/quality
  homework-service-full-en/files/docs   the same items and reports, in English
  homework-service-stage2/files/docs    stages 1 and 2 only, in Japanese
docs/quality is copied from skills/quality-summary-html/evals/homework-service-full(-en)/files/docs/quality.

The tables between <!-- generated: … --> markers are written by req-to-design's scripts/tables.py, as every stage writes
them before it commits; the cells that a report fills in by hand (a label, how a conflict is resolved, the flow of an
acceptance criterion…) are filled in here. So this script needs req-to-design: REQ_TO_DESIGN, else the REQ_TO_DESIGN
environment variable, else req-to-design next to this repository. It then runs req-to-design's scripts/check.py on each
case and prints the problems it finds; there should be none.

Planted on purpose, so that the evals can check the skill notices them:
- the stage 2 report's debt table, which the report writes by hand, leaves out DEC-06's debt (dec/DEC-06.yaml has it);
- finding numbers in YAML texts and report cells (「（FND-01 を受けて）」), which are revision notes the page removes;
- a retired driver (DRV-10), a CUJ walkthrough written as prose (CUJ-03), a latency budget without a table (NFR-02),
  common error contracts shared by two interfaces, and a hop table that the page draws as a chart (NFR-06), whose words
  are the Japanese report's own (ホップ, 余裕, 計);
- CUJ walkthroughs labelled with lines that end in a colon (Japanese) and with lines in bold (English);
- a row of the threat table that covers two flows (F4、F5);
- texts with more than one sentence and bracketed asides, which the page cuts to their gist (DEC-02's rationale,
  ELM-01's and ELM-02's responsibilities, DAT-02's consistency);
- hand-offs that are open (HND-02 of stage 2, HND-04 of stage 2b, HND-03 of stage 3) and decided (HND-01), an open
  assumption (DAS-01) and a request to the quality chain (QCR-01): the page shows only the open hand-offs;
- in English, the questions and answers under "## Decisions", which is not the decisions table ("## Design decisions").
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS = ROOT / 'skills' / 'design-summary-html' / 'evals'
QUALITY = ROOT / 'skills' / 'quality-summary-html' / 'evals'
DAY1, DAY2, DAY3, DAY4 = '2026-09-15', '2026-09-18', '2026-09-22', '2026-09-25'
S1, S2, S2B, S3 = ('requirements-to-architecture-drivers', 'architecture-drivers-to-architecture',
                   'architecture-to-technical-policy', 'architecture-to-high-level-design')


def data(lang, upto='3'):
    """Every item and report of the fictional design, in Japanese (ja) or English (en), up to stage 2 or stage 3"""
    def J(ja, en):
        return ja if lang == 'ja' else en

    full = upto == '3'
    SYS = J('課題提出サービス', 'Homework submission service')

    def common(i, title, basis='inferred', premises=(), status='active', note=None):
        return {'id': i, 'title': title, 'status': status, 'basis': basis, 'basis_note': note, 'premises': list(premises)}

    # ---------------- design-context.yaml
    ctx = {
        'read_from': {'quality_chain': 'docs/quality/', 'other': [J('利用者の入力（2026-09-15）', 'User input (2026-09-15)')]},
        'technology_constraints': [
            {'id': 'TC-01', 'statement': J('TypeScript で書く', 'Written in TypeScript'), 'kind': 'mandated',
             'source': J('利用者の入力', 'User input'), 'basis': 'stated'},
            {'id': 'TC-02', 'statement': J('提出したファイルは外部のストレージ（ObjectStore）に置く',
                                           'Submitted files are kept in an external storage service (ObjectStore)'),
             'kind': 'external-service', 'source': 'context.yaml EXT-01', 'basis': 'stated'},
            {'id': 'TC-03', 'statement': J('塾の既存のクラウドの一つの地域で動かす', "Runs in one region of the school's existing cloud account"),
             'kind': 'platform', 'source': J('利用者の入力、質問 2', 'User input, question 2'), 'basis': 'confirmed'},
            {'id': 'TC-04', 'statement': J('生徒と講師の画面は、ブラウザで動く Web アプリにする',
                                           'The screens for students and teachers are web apps that run in the browser'),
             'kind': 'platform', 'source': 'context.yaml DIN-01', 'basis': 'stated'},
        ],
        'project_constraints': [
            {'id': 'PC-01', 'kind': 'budget', 'statement': J('月 3 万円以内', 'Within 30,000 yen a month'),
             'source': J('利用者の入力', 'User input'), 'basis': 'stated'},
            {'id': 'PC-02', 'kind': 'deadline', 'statement': J('新学期（4 月）までに出す', 'Release before the new school year (April)'),
             'source': J('利用者の入力', 'User input'), 'basis': 'stated'},
            {'id': 'PC-03', 'kind': 'team', 'statement': J('開発者 2 人。運用の専任はいない', 'Two developers; no dedicated operations engineer'),
             'source': J('利用者の入力', 'User input'), 'basis': 'stated'},
        ],
        'teams': [{'id': 'TEAM-01', 'name': J('開発チーム', 'Development team'), 'owns': J('すべて', 'Everything'), 'basis': 'stated'}],
        'anticipated_changes': [{'id': 'CHG-01', 'change': J('保護者向けの画面を足す', 'Add screens for parents'),
                                 'expected': J('1 年以内', 'Within a year'), 'source': J('利用者の入力', 'User input'), 'basis': 'stated'}],
        'stakeholders': [{'id': 'STK-01', 'role': J('塾の経営者', "The cram school's owner"),
                          'concerns': [J('月の費用', 'Monthly cost'), J('新学期に間に合うこと', 'Ready for the new school year')],
                          'source': J('利用者の入力', 'User input'), 'basis': 'inferred'}],
    }
    labels = {'TC-01': 'TypeScript', 'TC-02': J('外部のストレージ', 'External storage'), 'TC-03': J('塾のクラウド', "The school's cloud"),
              'TC-04': J('Web アプリ', 'Web apps'), 'PC-01': J('月の費用', 'Monthly cost'), 'PC-02': J('新学期', 'New school year'),
              'PC-03': J('開発者 2 人', 'Two developers'), 'TEAM-01': J('開発チーム', 'Development team'),
              'CHG-01': J('保護者の画面', "Parents' screens"), 'STK-01': J('塾の経営者', 'Owner')}

    # ---------------- drivers
    def drv(i, title, kind, statement, sources, rank=None, business='high', breason='', difficulty='medium', dreason='',
            primary=False, scenario=None, negotiable=None, derived=(), conflicts=(), status='active', premises=()):
        d = common(i, title, premises=premises, status=status)
        d.update({'kind': kind, 'statement': statement, 'sources': list(sources),
                  'concern_of': ['USR-01'] if kind == 'quality' else ['STK-01'] if kind in ('constraint', 'change') else [],
                  'scenario': scenario, 'negotiable': negotiable, 'derived_from': list(derived),
                  'priority': None if kind == 'principle' else {'business': business, 'business_reason': breason,
                                                                'difficulty': difficulty, 'difficulty_reason': dreason, 'rank': rank},
                  'primary': primary, 'conflicts': [{'with': w, 'note': n} for w, n in conflicts], 'placeholders': []})
        return d

    def scen(source, stimulus, artifact, environment, response, measure):
        return {'source': source, 'stimulus': stimulus, 'artifact': artifact, 'environment': environment,
                'response': response, 'measure': measure}

    conflict = J('受領の前に記録を書くと、確定が遅くなる', 'Writing the record before the receipt slows the confirmation')
    drvs = [
        drv('DRV-01', J('締め切り前の集中でも提出を受け付け続ける', 'Keep accepting submissions in the rush before a deadline'), 'quality',
            J('締め切り前の 1 時間に提出が集中しても、提出を受け付け続ける', 'Keep accepting submissions even when they peak in the hour before a deadline'),
            ['QR-01', 'NFR-01', 'SLI-01', 'TC-02'], 1, 'high', J('QR-01 が重視（CUJ-01）', 'QR-01 is emphasized (CUJ-01)'),
            'high', J('提出が締め切り前に集中し、外部のストレージに頼る', 'Submissions peak before deadlines and rely on the external storage'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('締め切り前の 1 時間に提出する', 'Submit in the hour before a deadline'), 'FR-01',
                 J('締め切り前の集中（1 分に 300 件）', 'The rush before a deadline (300 submissions a minute)'),
                 J('提出が受け付けられ、受領が示される', 'The submission is accepted and the receipt is shown'),
                 J('NFR-01 の SLO（SLI-01 で数える）', "NFR-01's SLO, counted by SLI-01")),
            conflicts=[('DRV-02', conflict)], premises=['TC-02']),
        drv('DRV-02', J('提出の確定を待たせない', 'Confirm submissions without keeping students waiting'), 'quality',
            J('提出の確定を 3 秒以内に返す', 'Return the confirmation of a submission within 3 seconds'),
            ['QR-02', 'NFR-06'], 4, 'medium', J('QR-02 は最低限守る線', 'QR-02 is a minimum line'),
            'medium', J('記録を先に書く分だけ遅くなる（DRV-09）', 'Writing the record first adds time (DRV-09)'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('提出する', 'Submit'), 'FR-01, FR-02',
                 J('締め切り前の集中', 'The rush before a deadline'), J('受領が示される', 'The receipt is shown'),
                 J('NFR-06 の監視で、確定の 95 パーセンタイルが 3 秒以内', "NFR-06's monitor: the 95th percentile of confirmation within 3 seconds")),
            conflicts=[('DRV-01', conflict + J('（FND-01）', ' (FND-01)'))]),
        drv('DRV-03', J('受領の表示が提出の記録と一致する', 'Receipts match the submission records'), 'quality',
            J('受領を示した提出は、必ず記録に残っている', 'Every submission whose receipt is shown is in the records'),
            ['QR-03', 'QR-07', 'NFR-03', 'NFR-07'], 2, 'high', J('QR-03 と QR-07 が重視（CUJ-01、CUJ-04）', 'QR-03 and QR-07 are emphasized (CUJ-01, CUJ-04)'),
            'medium', J('ファイルの置き場所と記録の置き場所が別', 'The files and the records are kept in different places'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('提出する', 'Submit'), 'FR-02',
                 J('ふだんと締め切り前の集中', 'Normal operation and the rush before a deadline'),
                 J('受領と記録が一致する', 'The receipt matches the record'),
                 J('NFR-07 の監視で、受領と記録の食い違いが 0 件', "NFR-07's monitor: no receipt without a record"))),
        drv('DRV-04', J('保護者向けの画面を足せる', 'Screens for parents can be added'), 'change',
            J('保護者向けの画面を、今の画面と API を変えずに足せる', "Parents' screens can be added without changing the existing screens and APIs"),
            ['CHG-01'], 6, 'medium', J('将来の変更（CHG-01）', 'An anticipated change (CHG-01)'),
            'low', J('役割を足すだけで済む見込み', 'Adding a role is expected to be enough'), False,
            scen(J('開発チーム', 'Development team'), J('保護者の画面を足す', "Add the parents' screens"),
                 J('Web アプリと API', 'The web apps and the API'), J('リリースの後', 'After release'),
                 J('今の画面と API を変えずに足せる', 'Added without changing the existing screens and APIs'),
                 J('2 人で 4 週間以内', 'Within 4 weeks for two developers')), premises=['CHG-01']),
        drv('DRV-05', J('提出したファイルは外部のストレージに置く', 'Submitted files are kept in the external storage'), 'constraint',
            J('提出したファイルは外部のストレージ（ObjectStore）に置き、サーバーには置かない', 'Submitted files go to the external storage (ObjectStore), never to our servers'),
            ['TC-02'], 3, 'high', J('交渉できない制約', 'A non-negotiable constraint'),
            'medium', J('ストレージの障害で提出が止まりうる', 'A storage outage can stop submissions'), True, negotiable=False, premises=['TC-02']),
        drv('DRV-06', J('2 人で、月 3 万円以内で作って動かす', 'Built and run by two developers within 30,000 yen a month'), 'constraint',
            J('開発者 2 人が作って動かし、走る費用は月 3 万円以内', 'Two developers build and run it, for at most 30,000 yen a month'),
            ['PC-01', 'PC-03'], 5, 'high', J('交渉できない制約', 'A non-negotiable constraint'),
            'low', J('構成を小さく保てば満たせる', 'Met by keeping the structure small'), False, negotiable=False, premises=['PC-01', 'PC-03']),
        drv('DRV-07', J('一つのトレース ID で提出の失敗をたどる', 'Trace a failed submission with one trace ID'), 'observability',
            J('提出の失敗を、ブラウザからストレージまで一つのトレース ID でたどれる', 'A failed submission can be traced from the browser to the storage with one trace ID'),
            ['QR-10', 'FR-04', 'NFR-09'], 7, 'medium', J('QR-10 は最低限守る線', 'QR-10 is a minimum line'),
            'low', J('ログの欄をそろえれば済む', 'Consistent log fields are enough'), False,
            scen(J('開発者（USR-03）', 'Developers (USR-03)'), J('提出の失敗の知らせを受ける', 'Get the notice of a failed submission'), 'FR-04',
                 J('ふだん', 'Normal operation'), J('一つの ID で原因までたどれる', 'One ID leads to the cause'),
                 J('NFR-09 の完成の定義', "NFR-09's definition of done"))),
        drv('DRV-08', J('生徒の答案と個人情報を守る', "Protect students' answers and personal information"), 'security',
            J('提出と採点は、その生徒と担当の講師だけが開ける', 'Only the student and their teacher can open a submission and its grade'),
            ['QR-09', 'NFR-08'], 8, 'high', J('QR-09 が重視（法令）', 'QR-09 is emphasized (a law)'),
            'low', J('役割と担当の確かめで足りる', 'Checking the role and the class is enough'), False,
            scen(J('ほかの生徒', 'Another student'), J('他人の提出を開こうとする', "Tries to open someone else's submission"),
                 'FR-01, FR-03', J('ふだん', 'Normal operation'), J('開けない', 'It cannot be opened'),
                 J('NFR-08 の監査で違反 0 件', 'No violations in the NFR-08 audit'))),
        drv('DRV-09', J('記録を書いてから受領を示す', 'Write the record before showing the receipt'), 'principle',
            J('提出は、記録を書き終えてから受領を示す。受領を先に示さない', 'A submission shows its receipt only after its record is written, never before'),
            ['QR-07'], negotiable=False, derived=['DRV-03', 'DRV-01']),
        drv('DRV-10', J('旧ストレージを使う', 'Use the old storage'), 'constraint', J('旧ストレージに置く', 'Keep files in the old storage'),
            ['TC-02'], 9, negotiable=True, status='retired'),
    ]

    # ---------------- decisions
    def dec(i, stage, title, question, addresses, options, chosen, rationale, rejected, gains=(), costs=(),
            sensitive=(), trade_offs=(), assumptions=(), depends=(), parameters=(), debt=None, basis='inferred', premises=(), note=None):
        d = common(i, title, basis=basis, premises=premises, note=note)
        d.update({'stage': stage, 'question': question, 'addresses': list(addresses),
                  'options': [{'name': n, 'effect': e, 'cost': c} for n, e, c in options],
                  'chosen': chosen, 'rationale': rationale, 'rejected': [{'option': o, 'reason': r} for o, r in rejected],
                  'gains': list(gains), 'costs': list(costs), 'sensitive_points': list(sensitive),
                  'trade_offs': [{'with': w, 'note': n} for w, n in trade_offs], 'assumptions': list(assumptions),
                  'depends_on': list(depends), 'parameters': [{'name': n, 'value': v, 'basis': b} for n, v, b in parameters],
                  'debt': debt, 'as_is': 'new'})
        return d

    O1 = (J('一つの API サーバーと、生徒と講師の Web アプリ', 'One API server, and web apps for students and teachers'),
          J('2 人で作って動かせる', 'Two developers can build and run it'), J('サーバーが一つの障害の単位になる', 'The server is a single unit of failure'))
    O2 = (J('機能ごとのサービス', 'A service per function'), J('機能ごとに増やせる', 'Each function scales on its own'),
          J('2 人では動かしきれない', 'Too much for two developers to run'))
    O3 = (J('サーバーレスの関数', 'Serverless functions'), J('使った分だけ払う', 'Pay only for what is used'),
          J('手元で同じ形に動かしにくい', 'Hard to run the same way locally'))
    U1 = (J('署名付き URL で直接置く', 'Direct upload with a signed URL'), J('サーバーの負荷が増えない', 'No extra load on the server'),
          J('URL の期限を扱う', "The URLs' expiry must be handled"))
    U2 = (J('サーバーが受けて置く', 'The server receives and stores the file'), J('作りが単純', 'Simple to build'),
          J('締め切り前にサーバーが詰まる', 'The server chokes before deadlines'))
    R1 = (J('一つのトランザクションで記録を書き、受領を返す', 'Write the record in one transaction, then return the receipt'),
          J('受領と記録が食い違わない', 'Receipts never disagree with records'), J('確定が少し遅くなる', 'Confirmation is a little slower'))
    R2 = (J('受領を先に返し、記録は後で書く', 'Return the receipt first and write the record later'),
          J('確定が速い', 'Fast confirmation'), J('記録が欠けても受領が出る', 'A receipt can show without a record'))
    B1 = (J('毎晩のバッチ', 'A nightly batch'), J('費用が小さい', 'Low cost'), J('昼の提出は翌朝まで出ない', 'Daytime submissions appear the next morning'))
    B2 = (J('提出のたびに数える', 'Count on every submission'), J('すぐ出る', 'Shows at once'), J('提出の処理が重くなる', 'Slows submission processing'))
    T1 = (J('ブラウザがトレース ID を作り、見出しで渡す', 'The browser creates the trace ID and passes it in a header'),
          J('一つの ID でブラウザからストレージまでたどれる', 'One ID from the browser to the storage'), J('ログの欄をそろえる', 'Log fields must be consistent'))
    T2 = (J('サーバーが ID を作る', 'The server creates the ID'), J('作りが単純', 'Simple to build'),
          J('ブラウザで起きた失敗がつながらない', 'Failures in the browser are not linked'))
    P1 = (J('三つ目の Web アプリ', 'A third web app'), J('今の Web アプリを変えない', 'The existing web apps stay as they are'),
          J('配備するものが増える', 'One more thing to deploy'))
    P2 = (J('生徒の Web アプリに保護者の役割を足す', "A parent role in the students' web app"), J('配備するものが増えない', 'Nothing more to deploy'),
          J('生徒の画面の変更と重なる', "Changes overlap with the students' screens"))
    M1 = (J('一つのリポジトリ', 'One repository'), J('型と決まりを一か所で共有できる', 'Types and rules are shared in one place'),
          J('リポジトリが大きくなる', 'The repository grows'))
    M2 = (J('コンポーネントごとのリポジトリ', 'A repository per component'), J('それぞれ別に出せる', 'Each is released on its own'),
          J('2 人では揃えきれない', 'Too much for two developers to keep in line'))
    H1 = (J('Node.js の上の Hono', 'Hono on Node.js'), J('型のついた経路から仕様書を作れる', 'Specs come from typed routes'),
          J('仕組みが新しい', 'A newer framework'))
    H2 = (J('Node.js の上の Express', 'Express on Node.js'), J('情報が多い', 'Widely documented'),
          J('要求と応答に型がない', 'Requests and responses are untyped'))
    E1 = (J('問題の詳細（RFC 9457）に code と traceId を足す', 'Problem details (RFC 9457) with a code and a traceId'),
          J('標準の形で、道具が使える', 'A standard shape that tools understand'), J('欄が少し増える', 'A few more fields'))
    E2 = (J('独自の {code, message}', 'Our own {code, message}'), J('作りが単純', 'Simple to build'), J('道具の助けを失う', 'No help from tools'))
    K1 = (J('状態を変える要求すべてに冪等キー', 'An idempotency key on every state-changing request'),
          J('送り直しても二重にならない', 'Retries never duplicate'), J('キーを 24 時間持つ', 'Keys are kept for 24 hours'))
    K2 = (J('提出だけに冪等キー', 'An idempotency key on submissions only'), J('持つものが少ない', 'Less to keep'),
          J('返却の送り直しで通知が二重になる', 'A retried return sends two notifications'))
    decs = [
        dec('DEC-01', 'architecture', J('一つの API サーバーと二つの Web アプリにする', 'One API server and two web apps'),
            J('システムをどう分け、どこで動かすか', 'How is the system divided, and where does it run?'),
            ['DRV-06', 'DRV-01', 'DRV-04'], [O1, O2, O3], O1[0],
            J('上位の DRV-01 はどの案でも満たせ、DRV-06（2 人と費用）で一つのサーバーの案が勝つ。',
              'All options meet DRV-01; DRV-06 (two developers, the cost) decides for one server.'),
            [(O2[0], J('2 人では動かせない（DRV-06）', 'Two developers cannot run it (DRV-06)')),
             (O3[0], J('手元で同じ形にならない', 'Does not run the same way locally'))],
            gains=[J('配備するものが一つで済む', 'One thing to deploy')], costs=[J('一つの障害の単位になる', 'A single unit of failure')],
            sensitive=[J('サーバーのインスタンスの数', 'The number of server instances')],
            trade_offs=[('DRV-01', J('締め切り前の集中を一つのサーバーで受ける', 'One server takes the rush before deadlines'))],
            assumptions=[J('同時に使う生徒は 300 人まで（DAS-01）', 'At most 300 students at once (DAS-01)')],
            basis='assumed', premises=['DAS-01', 'PC-03']),
        dec('DEC-02', 'architecture', J('提出のファイルを署名付き URL でストレージに直接置く', 'Upload files straight to the storage with signed URLs'),
            J('提出のファイルを、サーバーを通さずにどう置くか', 'How are submitted files stored without passing through the server?'),
            ['DRV-01', 'DRV-05', 'DRV-02'], [U1, U2], U1[0],
            J('締め切り前の集中（DRV-01）で、サーバーがファイルを受けると詰まる。署名付き URL なら、ファイルはサーバーを通らない。',
              'In the rush before a deadline (DRV-01), a server receiving the files would choke. With signed URLs, files never pass through the server.'),
            [(U2[0], J('締め切り前に詰まる（DRV-01）', 'Chokes before deadlines (DRV-01)'))],
            gains=[J('締め切り前もファイルでサーバーの負荷が増えない', 'Files add no server load, even before deadlines')],
            costs=[J('URL の期限切れを扱う', 'Expired URLs must be handled')],
            sensitive=[J('署名付き URL の有効期限', "The signed URL's expiry")],
            trade_offs=[('DRV-08', J('URL を持つ人は期限まで置ける', 'Anyone holding the URL can upload until it expires'))],
            depends=['DEC-01'], premises=['EXT-01', 'TC-02'],
            parameters=[(J('署名付き URL の有効期限', 'Signed URL expiry'), J('15 分', '15 minutes'),
                         J('仮。提出の画面を開いてから送るまでの時間', 'Provisional; the time from opening the screen to submitting'))]),
        dec('DEC-03', 'architecture', J('記録を書いてから受領を示す', 'Write the record before showing the receipt'),
            J('受領の表示を、提出の記録とどう一致させるか', 'How do receipts stay in line with the submission records?'),
            ['DRV-03', 'DRV-09'], [R1, R2], R1[0],
            J('原則 DRV-09 に従う（FND-01 を受けて改めた）。受領を先に示すと、記録が欠けても受領が出る。',
              'It follows principle DRV-09 (changed after FND-01). Showing the receipt first lets a receipt show without a record.'),
            [(R2[0], J('記録が欠けうる（DRV-03）', 'Records can go missing (DRV-03)'))],
            gains=[J('受領が出たら必ず記録がある', 'A receipt always has a record')],
            costs=[J('確定に書き込みの時間が乗る（DRV-02）', 'The write adds to the confirmation time (DRV-02)')],
            sensitive=[J('記録の書き込みの時間', 'The time the write takes')],
            trade_offs=[('DRV-02', J('書き込みの分だけ確定が遅くなる', 'Confirmation is slower by the write'))],
            depends=['DEC-01'], note=J('FND-01 を受けて、受領を先に示す案から改めた', 'Changed after FND-01 from showing the receipt first')),
        dec('DEC-04', 'architecture', J('夜間のレポートをバッチで作る', 'Build the nightly report in a batch'),
            J('月次の提出状況のレポートをいつ作るか', 'When is the monthly submission report built?'),
            ['DRV-06', 'DRV-03'], [B1, B2], B1[0],
            J('塾の事務は月次で見る（CUJ-04）ので、毎晩で足りる。', 'The office reads it monthly (CUJ-04), so nightly is enough.'),
            [(B2[0], J('提出が重くなる（DRV-02）', 'Slows submissions (DRV-02)'))],
            gains=[J('費用が小さい', 'Low cost')], costs=[J('昼の提出は翌朝まで出ない', 'Daytime submissions appear the next morning')],
            sensitive=[J('バッチの起動の時刻', 'When the batch starts')], depends=['DEC-01'],
            parameters=[(J('バッチの起動', 'Batch start'), J('毎日 02:00', 'Daily at 02:00'),
                         J('NFR-02 の 6:00 まで 4 時間', "Four hours before NFR-02's 6:00"))],
            debt={'what': J('レポートは前の日までの分しか出ない', 'The report only covers up to the previous day'),
                  'why_accepted': J('塾の事務は月次で見る（CUJ-04）', 'The office reads it monthly (CUJ-04)'),
                  'repay_when': J('当日の数字が要ると言われたとき', 'When same-day numbers are asked for')}),
        dec('DEC-05', 'architecture', J('トレース ID をブラウザで作って引き継ぐ', 'The browser creates the trace ID and passes it on'),
            J('一つの提出の記録をどうつなぐか', 'How are the records of one submission linked?'),
            ['DRV-07'], [T1, T2], T1[0],
            J('CUJ-03 の調べを一つの ID から始められる（FND-02 を受けて足した）。',
              'A CUJ-03 investigation starts from one ID (added after FND-02).'),
            [(T2[0], J('ブラウザの失敗がつながらない（FND-02）', 'Browser failures are not linked (FND-02)'))],
            gains=[J('通知から原因まで一つの ID でたどれる', 'One ID from the notice to the cause')],
            costs=[J('ログの欄をそろえる', 'Log fields must be consistent')], depends=['DEC-01'],
            note=J('FND-02 を受けて足した', 'Added after FND-02')),
        dec('DEC-06', 'architecture', J('保護者向けの画面を生徒の Web アプリに置く', "The parents' screens go in the students' web app"),
            J('保護者向けの画面を、どの Web アプリにどう足すか', "Which web app gets the parents' screens, and how?"),
            ['DRV-04', 'DRV-06'], [P1, P2], P2[0],
            J('2 人で配備するものを増やさない（DRV-06）。画面の中身は、作ると決めたときに決める（HND-02）。',
              "Two developers do not add a thing to deploy (DRV-06). The screens' content is decided once they are decided on (HND-02)."),
            [(P1[0], J('配備するものが増える（DRV-06）', 'One more thing to deploy (DRV-06)'))],
            gains=[J('配備するものが増えない', 'Nothing more to deploy')], costs=[J('生徒の画面の変更と重なる', "Overlaps with changes to the students' screens")],
            depends=['DEC-01'], premises=['CHG-01'],
            debt={'what': J('保護者の画面と生徒の画面が一つのアプリにまとまる', "The parents' and the students' screens share one app"),
                  'why_accepted': J('2 人で配備するものを増やさない（DRV-06）', 'Two developers do not add a thing to deploy (DRV-06)'),
                  'repay_when': J('保護者だけの機能が三つを超えたとき', 'When parents have more than three features of their own')}),
        dec('DEC-07', 'technical-policy', J('すべてのコンポーネントを一つのリポジトリに置く', 'Keep every component in one repository'),
            J('リポジトリをいくつに分けるか', 'How many repositories are there?'),
            ['DRV-06'], [M1, M2], M1[0],
            J('2 人で型と決まりを揃えるには、一か所にまとめるのが安い（DRV-06）。', 'For two developers, one place is the cheapest way to keep types and rules in line (DRV-06).'),
            [(M2[0], J('2 人では揃えきれない（DRV-06）', 'Too much for two developers (DRV-06)'))],
            gains=[J('型を一か所で共有できる', 'Types are shared in one place')], costs=[J('リポジトリが大きくなる', 'The repository grows')],
            depends=['DEC-01'], premises=['PC-03']),
        dec('DEC-08', 'technical-policy', J('API サーバーは Node.js の上の Hono で書く', 'Write the API server with Hono on Node.js'),
            J('API サーバーをどのフレームワークで書くか', 'Which framework is the API server written in?'),
            ['DRV-02', 'DRV-07'], [H1, H2], H1[0],
            J('型のついた経路から仕様書を作れ、TypeScript（TC-01）で揃う。', 'Specs come from typed routes, all in TypeScript (TC-01).'),
            [(H2[0], J('要求と応答に型がない', 'Requests and responses are untyped'))],
            gains=[J('仕様書を手で書かずに済む', 'No spec written by hand')], costs=[J('仕組みが新しい', 'A newer framework')],
            depends=['DEC-01'], premises=['TC-01']),
        dec('DEC-09', 'high-level-design', J('エラーを問題の詳細の形で返す', 'Return errors as problem details'),
            J('すべての API で、エラーをどの形で返すか', 'In which shape do all APIs return errors?'),
            ['IFC-01', 'IFC-02'], [E1, E2], E1[0],
            J('標準の形にすると、画面と道具が同じ読み方をできる。', 'A standard shape lets the screens and the tools read errors the same way.'),
            [(E2[0], J('道具の助けを失う', 'No help from tools'))]),
        dec('DEC-10', 'high-level-design', J('状態を変える要求に冪等キーを求める', 'State-changing requests carry an idempotency key'),
            J('どの要求を冪等にするか', 'Which requests are idempotent?'),
            ['IFC-01', 'IFC-02', 'DRV-03'], [K1, K2], K1[0],
            J('提出も返却も、送り直しで二重にしない（DRV-03）。', 'Neither a submission nor a return may happen twice when retried (DRV-03).'),
            [(K2[0], J('返却が二重になる', 'Returns can happen twice'))],
            parameters=[(J('冪等キーの保持', 'Idempotency key retention'), J('24 時間', '24 hours'), J('仮', 'Provisional'))]),
    ]

    # ---------------- elements
    def elm(i, name, kind, resp, functions, drivers, decisions=(), team='TEAM-01', technology=None, runs_on='ELM-07', depends=(), premises=()):
        d = common(i, name, premises=premises)
        d.update({'kind': kind, 'name': name, 'responsibility': resp, 'functions': list(functions), 'drivers': list(drivers),
                  'decisions': list(decisions), 'team': team, 'technology': technology, 'runs_on': runs_on,
                  'depends_on': list(depends), 'as_is': 'new'})
        return d
    browser = J('生徒と講師のブラウザ（DEC-01）', "The students' and teachers' browsers (DEC-01)")
    container = J('Node.js、コンテナで（DEC-01）', 'Node.js, in a container (DEC-01)')
    elms = [
        elm('ELM-01', J('生徒の Web アプリ', 'Student web app'), 'component',
            J('課題を開き、ファイルをストレージに直接置き、提出して受領を示す。下書きを保存し、保護者の画面も持つ',
              "Opens assignments, uploads files straight to the storage, submits and shows receipts. Saves drafts and holds the parents' screens"),
            ['FR-01', 'FR-02', 'FR-06'], ['DRV-01', 'DRV-02', 'DRV-03', 'DRV-04'], ['DEC-01', 'DEC-02', 'DEC-05', 'DEC-06'],
            technology=browser, runs_on=None, depends=['ELM-03', 'ELM-05'], premises=['TC-04']),
        elm('ELM-02', J('講師の Web アプリ', 'Teacher web app'), 'component',
            J('提出を開き、採点して返却する。月次のレポートを見る', 'Opens submissions, grades and returns them. Shows the monthly report'),
            ['FR-03', 'FR-05', 'FR-08'], ['DRV-08'], ['DEC-01'], technology=browser, runs_on=None, depends=['ELM-03'], premises=['TC-04']),
        elm('ELM-03', J('API サーバー', 'API server'), 'component',
            J('提出の確定と受領、署名付き URL、採点と返却、トレース ID の記録', 'Confirms submissions and receipts, issues signed URLs, grading and returns, records trace IDs'),
            ['FR-01', 'FR-02', 'FR-03', 'FR-04', 'FR-05', 'FR-06', 'FR-08', 'FR-09'], ['DRV-01', 'DRV-02', 'DRV-03', 'DRV-05', 'DRV-07', 'DRV-08', 'DRV-09'],
            ['DEC-01', 'DEC-02', 'DEC-03', 'DEC-05'], technology=container, depends=['ELM-04', 'ELM-05']),
        elm('ELM-04', J('データベース', 'Database'), 'data-store', J('課題、提出の記録、採点を持つ', 'Holds assignments, submission records and grades'),
            [], ['DRV-03'], ['DEC-03'], technology=J('マネージドの PostgreSQL（TC-03）', 'Managed PostgreSQL (TC-03)'), premises=['TC-03']),
        elm('ELM-05', J('外部のストレージ', 'External storage'), 'data-store', J('提出のファイルを置く（外部のサービスの ObjectStore）', 'Keeps the submitted files (the external ObjectStore service)'),
            [], ['DRV-05'], ['DEC-02'], team=None, technology='ObjectStore（TC-02）' if lang == 'ja' else 'ObjectStore (TC-02)',
            runs_on=None, premises=['EXT-01', 'TC-02']),
        elm('ELM-06', J('夜間のバッチ', 'Nightly batch'), 'component', J('毎晩、提出状況のレポートを作る', 'Builds the submission report every night'),
            ['FR-05', 'FR-09'], ['DRV-06'], ['DEC-04'], technology=container, depends=['ELM-04']),
        elm('ELM-07', J('クラウドの実行環境', 'Cloud runtime'), 'node', J('API サーバーと夜間のバッチを動かす', 'Runs the API server and the nightly batch'),
            [], [], ['DEC-01'], technology=J('塾のクラウドのコンテナの実行環境（TC-03）', "The school cloud's container runtime (TC-03)"),
            runs_on=None, premises=['TC-03']),
    ]

    # ---------------- technical policies (stage 2b)
    def pol(i, title, scope, addresses, decisions, rules, fields, premises=(), basis='inferred'):
        d = common(i, title, basis=basis, premises=premises)
        d.update({'scope': scope, 'addresses': list(addresses), 'decisions': list(decisions),
                  'rules': [{'rule': r, 'check': c} for r, c in rules]})
        d.update(fields)
        d['as_is'] = 'new'
        return d
    pols = [
        pol('POL-01', J('コンポーネントの種類ごとの技術の組み合わせ', 'The stack of each kind of component'), 'technology',
            ['DRV-06', 'DRV-07'], ['DEC-01', 'DEC-08'],
            [(J('パッケージの管理は pnpm の一つの workspace で行う', 'Packages are managed in one pnpm workspace'),
              J('検査の手順がロックファイルを変えない入れ方で依存を入れる', 'The check step installs without changing the lockfile'))],
            {'stack': [
                {'kind': J('ブラウザで動く Web アプリ', 'Web app in the browser'), 'elements': ['ELM-01', 'ELM-02'], 'language': 'TypeScript',
                 'runtime': J('生徒と講師のブラウザの今の版と一つ前の版', "The students' and teachers' browsers, in their current release and the one before it"),
                 'framework': 'React', 'libraries': [J('Vite（ビルド）', 'Vite (build)'), J('React Router（画面の移り変わり）', 'React Router (screen flow)')]},
                {'kind': J('HTTP のサーバーと夜間のバッチ', 'HTTP server and nightly batch'), 'elements': ['ELM-03', 'ELM-06'], 'language': 'TypeScript',
                 'runtime': J('Node.js の Active LTS の版を、コンテナで（DAS-02）', 'The Active LTS version of Node.js, in a container (DAS-02)'),
                 'framework': J('Hono（DEC-08）', 'Hono (DEC-08)'),
                 'libraries': [J('Zod（要求の確かめ）', 'Zod (request validation)'), J('ObjectStore の SDK（署名付き URL、DEC-02）', 'The ObjectStore SDK (signed URLs, DEC-02)')]}]},
            premises=['TC-01', 'TC-04', 'DAS-02']),
        pol('POL-02', J('一つのリポジトリと、その依存の規則', 'One repository and its dependency rules'), 'repository',
            ['DRV-06'], ['DEC-07'],
            [(J('アプリのディレクトリは機能ごとに分ける', "Each app's directories are split by business capability"),
              J('プルリクエストのレビュー', 'The review of the pull request'))],
            {'repositories': [{'name': J('homework-service（docs と apps/ を持つ一つのリポジトリ）', 'homework-service (one repository holding docs and apps/)'),
                               'holds': ['ELM-01', 'ELM-02', 'ELM-03', 'ELM-06']}],
             'dependency_rules': [{'rule': J('apps/ の下のアプリは互いに import しない', 'The apps under apps/ never import each other'),
                                   'check': J('リンターの no-restricted-imports を検査の手順で', 'The linter rule no-restricted-imports in the check step')}]},
            premises=['PC-03']),
        pol('POL-03', J('テストの層とゲートの出どころ', 'Test layers and where the gates are checked'), 'testing',
            ['DRV-01', 'DRV-03'], ['DEC-03'],
            [(J('受け入れ基準は、確かめられるいちばん下の層で確かめる', 'Each acceptance criterion is checked at the lowest layer that can check it'),
              J('プルリクエストのレビュー', 'The review of the pull request'))],
            {'layers': [
                {'layer': J('単体', 'Unit'), 'covers': J('一つのモジュールの規則（判断と計算）', "One module's rules (decisions and calculations)"),
                 'replaces': J('モジュールの外のすべて', 'Everything outside the module'), 'runs': J('検査の手順で、変更のたび', 'In the check step, on every change')},
                {'layer': J('結合', 'Integration'), 'covers': J('ELM-03 を HTTP の境界から、自身のデータベースとともに', 'ELM-03 from its HTTP boundary, with its own database'),
                 'replaces': J('外部のストレージ（下の偽物）', 'The external storage (the double below)'), 'runs': J('検査の手順で、コンテナのデータベースに対して', 'In the check step, against a database in a container')},
                {'layer': J('端から端', 'End-to-end'), 'covers': J('CUJ-01 と CUJ-02 を画面から', 'CUJ-01 and CUJ-02 from the screens'),
                 'replaces': J('なし', 'Nothing'), 'runs': J('リリースの手順で、試験の環境に対して', "In the release step, against the staging environment")}],
             'doubles': [{'replaces': J('ELM-05、外部のストレージ', 'ELM-05, the external storage'),
                          'with': J('署名付き URL に答え、期限切れと失敗を返せる偽物', 'A fake that answers signed URLs and can expire or fail them'),
                          'seam': J('ELM-03 のストレージのアダプター', "ELM-03's storage adapter")}],
             'environments': [{'name': 'CI', 'runs': J('検査の手順', 'The check step'), 'data': J('テストごとに作る', 'Built in each test')}],
             'gate_bindings': [
                 {'nfr': 'NFR-03', 'where': J('リリースの手順の端から端の層', "The release step's end-to-end layer"), 'by': J('受領の表示のテスト', 'The receipt tests')},
                 {'nfr': 'NFR-04', 'where': J('検査の手順', 'The check step'), 'by': J('提出の処理の単体と結合のテスト', 'The unit and integration tests of submission')},
                 {'nfr': 'NFR-09', 'where': J('プルリクエストの完成の定義', "The pull request's definition of done"), 'by': J('レビューする人', 'The reviewer')},
                 {'nfr': 'NFR-10', 'where': J('プルリクエストの完成の定義', "The pull request's definition of done"), 'by': J('もう一人の講師の確かめ', "A second teacher's check")}],
             'audit_bindings': [
                 {'nfr': 'NFR-08', 'where': J('四半期ごとのチケット', 'A ticket every quarter'), 'by': J('塾の事務が行う', 'The office performs it')},
                 {'nfr': 'NFR-11', 'where': J('半年ごとのチケット', 'A ticket every half year'), 'by': J('開発者が行う', 'A developer performs it')}]}),
        pol('POL-04', J('パイプラインとコードの中の約束事', 'The pipeline and the conventions inside the code'), 'pipeline-and-code',
            ['DRV-06', 'DRV-07'], ['DEC-05'],
            [(J('ログは trace_id を持つ構造化ログで書く', 'Logs are structured and carry the trace_id'),
              J('結合の層のテスト', 'The integration tests'))],
            {'pipeline': [
                {'step': 'check', 'when': J('main に入る変更のたび', 'On every change to main'),
                 'runs': J('型の確かめ、リンター、単体と結合のテスト', 'Type checks, the linter, unit and integration tests'), 'blocks': J('main に入れること', 'Merging to main')},
                {'step': 'release', 'when': J('版の印を付けたとき', 'When a version tag is set'),
                 'runs': J('端から端のテストと、イメージを一度だけ作ること', 'End-to-end tests, and building the image once'), 'blocks': J('配備', 'Deployment')}]}),
        pol('POL-05', J('インタフェースの種類ごとの仕様書の作り方', 'How the spec of each kind of interface is made'), 'specs',
            ['DRV-06'], ['DEC-08'], [],
            {'specs': [
                {'interfaces': J('ELM-03 が提供する HTTP の操作（IFC-01、IFC-02）', 'The HTTP operations ELM-03 provides (IFC-01, IFC-02)'), 'made': 'from-code',
                 'how': J('Hono の経路の定義から OpenAPI の文書を生成する', 'An OpenAPI document generated from the Hono routes')},
                {'interfaces': J('ストレージへのファイル（IFC-03）', 'Files in the storage (IFC-03)'), 'made': 'owner',
                 'how': J('ObjectStore の文書を IFC が引く', "The IFC cites ObjectStore's documentation")},
                {'interfaces': J('夜間のバッチ（IFC-04）', 'The nightly batch (IFC-04)'), 'made': 'none',
                 'how': J('IFC が決まり', 'The IFC is the contract')}]}),
        pol('POL-06', J('実装からの戻り', 'Feedback from implementation'), 'implementation-feedback', ['DRV-06'], [],
            [(J('設計どおりにできないときは、指摘を書いて段階を再実行する', 'When the code cannot keep the design, write a finding and re-run the stage'),
              J('プルリクエストのレビュー', 'The review of the pull request'))], {}),
    ]

    # ---------------- interfaces
    def ifc(i, name, kind, provider, consumers, functions, operations, errors, sli=(), premises=(), note=None):
        d = common(i, name, premises=premises, note=note)
        d.update({
            'kind': kind, 'name': name, 'provider': provider, 'consumers': list(consumers), 'functions': list(functions),
            'operations': [{'name': n, 'does': x} for n, x in operations], 'format': 'JSON', 'protocol': 'HTTPS',
            'auth': J('セッションのクッキー', 'Session cookie'),
            'errors': [{'case': c, 'signal': s, 'caller_does': x} for c, s, x in errors],
            'idempotency': J('状態を変える要求は Idempotency-Key（DEC-10）', 'State-changing requests carry an Idempotency-Key (DEC-10)'),
            'timing': {'timeout': J('ブラウザ 10 秒', 'Browser 10 s'), 'ordering': None, 'delivery': None},
            'versioning': J('経路に v1', 'v1 in the path'), 'observability': J('トレース ID をログに書く', 'Trace IDs in the logs'),
            'sli_bindings': [{'sli': s, 'events': e, 'fields': f, 'method': m} for s, e, f, m in sli],
            'spec': None, 'as_is': 'new'})
        return d
    common_errors = [
        (J('共通: ログインしていない', 'Common: not signed in'), '401 UNAUTHENTICATED', J('ログインの画面へ', 'Go to the sign-in screen')),
        (J('共通: 要求の形が違う', 'Common: the request is malformed'), '400 INVALID_REQUEST', J('欄を直す', 'Fix the fields')),
    ]
    ifcs = [
        ifc('IFC-01', J('提出の API', 'Submission API'), 'http', 'ELM-03', ['ELM-01'], ['FR-01', 'FR-02', 'FR-04', 'FR-06'],
            [('POST /api/v1/uploads', J('署名付き URL を返す', 'Returns a signed URL')),
             ('POST /api/v1/submissions', J('提出を確定し、受領を返す', 'Confirms the submission and returns the receipt')),
             ('GET /api/v1/submissions/{id}', J('提出と受領を返す', 'Returns the submission and its receipt')),
             ('PUT /api/v1/drafts/{id}', J('下書きを保存する', 'Saves the draft'))],
            [('POST /api/v1/submissions: ' + J('締め切りを過ぎた', 'the deadline has passed'), '409 DEADLINE_PASSED',
              J('締め切りを過ぎたと示す', 'Show that the deadline has passed')),
             ('POST /api/v1/submissions: ' + J('ファイルがストレージにない', 'the file is not in the storage'), '422 FILE_MISSING',
              J('もう一度ファイルを置く', 'Upload the file again'))] + common_errors,
            sli=[('SLI-01', J('ELM-03 が受けた POST /api/v1/submissions の要求ごと', 'Each POST /api/v1/submissions request that ELM-03 receives'),
                  ['route', 'status', 'trace_id'], J('ELM-03 の要求のログ', "ELM-03's request log"))]),
        ifc('IFC-02', J('採点の API', 'Grading API'), 'http', 'ELM-03', ['ELM-02'], ['FR-03', 'FR-05', 'FR-08'],
            [('GET /api/v1/teacher/submissions', J('担当の提出の一覧', "Lists the teacher's submissions")),
             ('PUT /api/v1/teacher/submissions/{id}/grade', J('採点を保存する', 'Saves the grade')),
             ('POST /api/v1/teacher/submissions/{id}/return', J('返却して通知する', 'Returns the submission and notifies')),
             ('GET /api/v1/teacher/reports/monthly', J('月次のレポートを返す', 'Returns the monthly report'))],
            [('POST /api/v1/teacher/submissions/{id}/return: ' + J('採点が済んでいない', 'not graded yet'), '409 NOT_GRADED',
              J('採点を促す', 'Ask for the grade first'))] + common_errors),
        ifc('IFC-03', J('ストレージへのファイル', 'Files in the storage'), 'file', 'ELM-05', ['ELM-01', 'ELM-03'], ['FR-01'],
            [(J('署名付き URL への PUT', 'PUT to the signed URL'), J('ファイルを置く', 'Stores the file'))],
            [(J('URL の期限切れ', 'The URL has expired'), '403 (ObjectStore)', J('新しい URL をもらう', 'Get a new URL'))], premises=['EXT-01'],
            note=J('HND-01 を決めた: PUT は確定の区間の外にある', 'Decides HND-01: the PUT is outside the confirmation hops')),
        ifc('IFC-04', J('夜間の提出状況レポート', 'Nightly submission report'), 'batch', 'ELM-06', ['ELM-02'], ['FR-05', 'FR-09'],
            [(J('nightly-report ジョブ', 'nightly-report job'), J('前の日までの提出を数えて書く', 'Counts the submissions up to the previous day'))],
            [(J('前の日の分が終わっていない', 'The previous day is not finished'), J('終わっていない日から続ける', 'Continues from the unfinished day'),
              J('なし', 'Nothing'))],
            sli=[('SLI-02', J('nightly-report ジョブの一回の実行ごと', 'Each run of the nightly-report job'), ['finished_at', 'status'],
                  J('ELM-06 の終わりの記録', "ELM-06's completion record"))]),
    ]

    # ---------------- data
    def dat(i, entity, owner, store, consistency, retention, classification, relations=()):
        d = common(i, entity)
        d.update({'entity': entity, 'owner': owner, 'store': store, 'key_attributes': [],
                  'relations': [{'to': t, 'kind': k, 'note': n} for t, k, n in relations],
                  'consistency': consistency, 'retention': retention, 'classification': classification, 'drivers': [],
                  'sli_bindings': [], 'as_is': 'new'})
        return d
    dats = [
        dat('DAT-01', J('課題', 'Assignment'), 'ELM-03', 'ELM-04', J('講師の要求ごとに書く', 'Written per request from teachers'),
            J('学年の終わりまで', 'Until the end of the school year'), 'internal', [('DAT-02', 'one-to-many', J('提出', 'Submissions'))]),
        dat('DAT-02', J('提出', 'Submission'), 'ELM-03', 'ELM-04',
            J('提出の記録と受領を一つのトランザクションで書く（DEC-03）。受領の番号は記録の ID から作る',
              "The record and the receipt are written in one transaction (DEC-03). The receipt number comes from the record's ID"),
            J('卒業の後 1 年', 'One year after graduation'), 'personal', [('DAT-03', 'one-to-one', J('ファイル', 'File'))]),
        dat('DAT-03', J('提出のファイル', 'Submitted file'), 'ELM-03', 'ELM-05', J('署名付き URL で一度だけ置く', 'Uploaded once through a signed URL'),
            J('卒業の後 1 年', 'One year after graduation'), J('personal（生徒の答案）', "personal (students' answers)")),
        dat('DAT-04', J('採点', 'Grade'), 'ELM-03', 'ELM-04', J('講師の採点ごとに書く', 'Written per grading'),
            J('卒業の後 1 年', 'One year after graduation'), 'personal'),
    ]

    # ---------------- hand-offs, findings, assumptions, requests
    def hnd(i, title, frm, to, component, origin, what, bounds, trigger, status='open', resolution=None):
        d = common(i, title, status=status)
        d.update({'from': frm, 'to': to, 'component': component, 'origin': list(origin), 'what': what, 'bounds': bounds,
                  'trigger': trigger, 'resolution': resolution})
        return d
    hnds = [
        hnd('HND-01', J('ストレージが PUT に答えるまでの時間', 'How fast the storage answers a PUT'), S1, S3, None, ['QR-02'],
            J('ObjectStore が署名付き URL への PUT にどれだけの時間で答えるか', 'How long ObjectStore takes to answer a PUT to a signed URL'),
            J('NFR-06 のしきい値、DRV-02', "NFR-06's threshold, DRV-02"), J('第 3 段階の次の実行', 'The next run of stage 3'),
            status='decided' if full else 'open',
            resolution=J('IFC-03 で確かめた。PUT は確定の区間の外にある', 'Confirmed in IFC-03: the PUT is outside the confirmation hops') if full else None),
        hnd('HND-02', J('保護者の画面の並び', "The layout of the parents' screens"), S2, 'high-level-design-to-detailed-design', 'ELM-01', ['DEC-06'],
            J('保護者の画面の並びと、生徒の画面との分け方', "The layout of the parents' screens, and how they are kept apart from the students'"),
            J('DEC-06、DRV-04', 'DEC-06, DRV-04'), J('保護者の画面を作ると決めたとき', "When the parents' screens are decided on")),
        hnd('HND-03', J('API の要求と応答のスキーマ', 'The schemas of the API requests and responses'), S3, 'implementation', 'ELM-03', ['IFC-01', 'IFC-02'],
            J('IFC-01 と IFC-02 の要求と応答のスキーマ', 'The schemas of the requests and responses of IFC-01 and IFC-02'),
            J('IFC-01 と IFC-02 の操作とエラーの決まり（DEC-09）', 'The operations and error contracts of IFC-01 and IFC-02 (DEC-09)'),
            J('ELM-03 の API を実装するとき', "When ELM-03's API is implemented")),
        hnd('HND-04', J('CI のジョブの並べ方', 'How the CI jobs are arranged'), S2B, 'implementation', 'ELM-03', ['POL-04'],
            J('検査の手順のジョブの並べ方と、キャッシュの持ち方', 'How the jobs of the check step are arranged, and what they cache'),
            J('POL-04 の手順と、それが止めるもの', "POL-04's steps and what they block"), J('パイプラインを組むとき', 'When the pipeline is set up')),
    ]
    fnds = [
        dict(common('FND-01', J('受領を記録より先に示している', 'The receipt is shown before the record is written'), status='accepted'),
             raised_by='design-review', raised_in='reviews/2-architecture.md', to=S2, targets=['DEC-03'], severity='major',
             evidence=J('受領の後に記録が欠けうる', 'A record can go missing after the receipt'),
             suggestion=J('記録を書いてから受領を返す', 'Write the record, then return the receipt'),
             resolution=J('受け入れ。DEC-03 を直した', 'Accepted; DEC-03 changed')),
        dict(common('FND-02', J('トレース ID の引き継ぎがない', 'No trace ID is passed on'), status='accepted'),
             raised_by='design-review', raised_in='reviews/2-architecture.md', to=S2, targets=['DEC-05'], severity='minor',
             evidence=J('ブラウザの失敗がつながらない', 'Browser failures are not linked'),
             suggestion=J('ブラウザで ID を作る', 'Create the ID in the browser'), resolution=J('受け入れ。DEC-05 を足した', 'Accepted; DEC-05 added')),
    ]
    dases = [
        {'id': 'DAS-01', 'title': J('同時に使う生徒は 300 人まで', 'At most 300 students at once'), 'status': 'open', 'stage': '2', 'kind': 'judgment',
         'statement': J('締め切り前に同時に提出する生徒は 300 人までとする', 'At most 300 students submit at once before a deadline'),
         'why_unsure': J('塾の生徒の数は入力にない', "The school's number of students is not in the inputs"), 'breadth': 'medium', 'severity': 'low',
         'rating_note': J('DEC-01 だけが頼る。超えたらインスタンスを足す', 'Only DEC-01 relies on it; beyond it, instances are added'),
         'answer': None, 'answered_in': None},
        {'id': 'DAS-02', 'title': J('Node.js の Active LTS の版を使う', 'Use the Active LTS version of Node.js'), 'status': 'confirmed', 'stage': '2b',
         'kind': 'decision', 'statement': J('API サーバーと夜間のバッチは Node.js の Active LTS の版で動かす', 'The API server and the nightly batch run on the Active LTS version of Node.js'),
         'why_unsure': J('版の決まりは入力にない', 'No version rule is in the inputs'), 'breadth': 'low', 'severity': 'low',
         'rating_note': J('POL-01 だけが頼る', 'Only POL-01 relies on it'), 'answer': J('そのとおり', 'As drafted'),
         'answered_in': J('第 2b 段階の質問 1', 'stage 2b, question 1')},
    ]
    qcrs = [
        {'id': 'QCR-01', 'title': J('NFR-06 の測る区間', "What NFR-06 measures"), 'status': 'open', 'stage': '3', 'targets': ['NFR-06'],
         'origin': ['IFC-01', 'IFC-03'],
         'issue': J('NFR-06 の 3 秒が、ストレージへのファイルの PUT を含むかが分からない', "NFR-06's 3 seconds do not say whether they include the PUT of the file to the storage"),
         'suggestion': J('NFR-06 の測る区間に、ストレージへの PUT を含めないと書く', "Say that NFR-06's measured span leaves out the PUT to the storage"),
         'quality_stages': [4], 'impact': 'low', 'impact_note': J('予算の表の区間が一つ変わるだけ', 'Only one hop of the budget would change'),
         'answer': None, 'answered_in': None},
    ]

    # ---------------- reports
    def table(head, rows):
        out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
        out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
        return '\n'.join(out)

    def gen(name):
        return f'<!-- generated: {name} -->\n<!-- /generated -->'

    def mmd(src):
        return '```mermaid\n' + src.strip('\n') + '\n```'

    def status(day, n):
        return J(f'状態: 回答反映済み · 更新: {day} · 入力の基準: なし · 第 {n} 段階（全 4 段階）',
                 f'Status: answers applied · Updated: {day} · Inputs as of: none · Stage {n} of 4')

    def closing(nxt, decided=None, handoffs=True):
        out = [f'## {J("指摘", "Findings")}', gen('findings'), '']
        if handoffs:
            out += [f'## {J("申し送り", "Hand-offs")}', gen('handoffs'), '']
        out += [f'## {J("決めたこと", "Decisions")}',
                table(['#', J('質問', 'Question'), J('回答', 'Answer'), J('項目', 'Items')], decided or []), '',
                f'## {J("未確認の仮定", "Open assumptions")}', gen('assumptions'), '',
                f'## {J("未定の値", "Placeholders")}', '', J('なし。', 'None.'), '',
                f'## {J("未解決の点", "Open gaps")}', '', J('なし。', 'None.'), '',
                f'## {J("範囲外", "Out of scope")}', '', J('保護者向けの画面の中身（CHG-01）。', "The content of the parents' screens (CHG-01)."), '',
                f'## {J("次", "Next")}', '', nxt, '']
        return out

    r1 = [f'# {J("設計を動かす要求", "Architecture drivers")}: {SYS}', '', status(DAY1, 1), '',
          f'## {J("概要", "Summary")}', '',
          J('主な設計を動かす要求は四つ（締め切り前の集中、受領と記録の一致、外部のストレージ、確定の速さ）。費用と体制では実現できる見込み。',
            'Four primary drivers (the deadline rush, receipts matching records, the external storage, fast confirmation). Feasible with this budget and team.'), '',
          f'## {J("入力", "Inputs")}',
          table([J('出どころ', 'Source'), J('得たもの', 'What it gave')],
                [['docs/quality/', J('利用者、CUJ、FR、QR、NFR、SLI', 'Users, CUJs, FRs, QRs, NFRs, SLIs')],
                 [J('利用者の入力（2026-09-15）', 'User input (2026-09-15)'), J('技術制約、費用・納期・体制', 'Technology and project constraints')]]), '',
          f'## {J("境界と外部", "Boundary and the outside")}',
          table([J('外部', 'Outside'), J('種類', 'Kind'), J('システムとの受け渡し', 'Exchanges with the system through')],
                [[J('USR-01 生徒', 'USR-01 Students'), J('利用者', 'User'), J('画面（FR-01、FR-02、FR-06）', 'Screens (FR-01, FR-02, FR-06)')],
                 [J('USR-02 講師', 'USR-02 Teachers'), J('利用者', 'User'), J('画面（FR-03、FR-05、FR-08）', 'Screens (FR-03, FR-05, FR-08)')],
                 [J('EXT-01 外部のストレージ', 'EXT-01 External storage'), J('外部のシステム', 'External system'), J('ファイル（FR-01）', 'Files (FR-01)')]]), '',
          f'## {J("今の構造", "Current structure")}', '', J('新しく作る。今のコードはない。', 'Built from scratch; there is no code yet.'), '',
          f'## {J("設計の与件", "Design context")}', gen('design-context'), '',
          f'## {J("関心事の一覧", "Concern inventory")}',
          table([J('入力の項目', 'Input item'), J('種類', 'Kind'), J('誰の関心事', 'Whose concern'), J('なったもの', 'Became')],
                [['QR-01', J('品質', 'Quality'), 'USR-01', 'DRV-01'], ['QR-02', J('品質', 'Quality'), 'USR-01', 'DRV-02'],
                 [J('QR-03、QR-07', 'QR-03, QR-07'), J('品質', 'Quality'), J('USR-01、USR-04', 'USR-01, USR-04'), 'DRV-03'],
                 ['QR-09', J('品質', 'Quality'), 'USR-01', 'DRV-08'], ['QR-10', J('品質', 'Quality'), 'USR-03', 'DRV-07'],
                 ['TC-02', J('制約', 'Constraint'), 'STK-01', 'DRV-05'], [J('PC-01、PC-03', 'PC-01, PC-03'), J('制約', 'Constraint'), 'STK-01', 'DRV-06'],
                 ['CHG-01', J('変更', 'Change'), 'STK-01', 'DRV-04'],
                 ['QR-04', J('品質', 'Quality'), 'USR-02', J('置いた: 今期は対象外', 'set aside: excluded this cycle')]]), '',
          f'## {J("設計を動かす要求", "Architecture drivers")}', gen('drivers'), '',
          f'## {J("順位表", "Ranking table")}', gen('ranking'), '',
          J('主な要求は順位 4 まで。', 'The first four are primary.'), '',
          f'## {J("競合", "Conflicts")}', gen('conflicts'), '',
          f'## {J("実現できるか", "Feasibility")}',
          table(['DRV', J('この費用、納期、体制で知られたやり方があるか', 'Known way with this budget, deadline and team'), J('理由', 'Why')],
                [['DRV-01', J('ある', 'Yes'), J('ファイルをサーバーに通さなければ、一つのサーバーで受けられる', 'One server is enough if files do not pass through it')],
                 ['DRV-03', J('ある', 'Yes'), J('一つのトランザクションで書く', 'Written in one transaction')],
                 ['DRV-05', J('ある', 'Yes'), J('ObjectStore の署名付き URL を使う', "With ObjectStore's signed URLs")],
                 ['DRV-02', J('ある見込み', 'Likely'), J('確定の区間の予算で確かめる', 'Checked with the hop budgets of confirmation')]]), ''] + closing(
          J('architecture-drivers-to-architecture を実行する。', 'Run architecture-drivers-to-architecture.'),
          [['1', J('締め切り前の最大の件数は？', 'The peak number of submissions before a deadline?'), J('1 分に 300 件（下書きどおり）', '300 a minute (as drafted)'), 'DRV-01']])

    walk = {
        'CUJ-01': [[J('課題を開く', 'Open the assignment'), 'FR-01', J('ELM-01、ELM-03', 'ELM-01, ELM-03'), J('ELM-01 → ELM-03 課題の取得', 'ELM-01 → ELM-03 gets the assignment'), J('なし', 'none')],
                   [J('ファイルを添付する', 'Attach a file'), 'FR-01', J('ELM-01、ELM-05', 'ELM-01, ELM-05'), J('ELM-01 → ELM-05 署名付き URL で置く', 'ELM-01 → ELM-05 upload with a signed URL'), J('なし', 'none')],
                   [J('提出する', 'Submit'), J('FR-01、FR-02', 'FR-01, FR-02'), J('ELM-01、ELM-03、ELM-04', 'ELM-01, ELM-03, ELM-04'), J('ELM-03 が記録を書いて受領を返す', 'ELM-03 writes the record and returns the receipt'), J('なし', 'none')]],
        'CUJ-02': [[J('提出を開く', 'Open the submission'), 'FR-03', J('ELM-02、ELM-03、ELM-05', 'ELM-02, ELM-03, ELM-05'), J('ELM-02 → ELM-03 一覧と内容', 'ELM-02 → ELM-03 list and contents'), J('なし', 'none')],
                   [J('採点する', 'Grade'), 'FR-03', J('ELM-02、ELM-03', 'ELM-02, ELM-03'), J('採点を保存する', 'Saves the grade'), J('なし', 'none')],
                   [J('返却する', 'Return'), J('FR-03、FR-08', 'FR-03, FR-08'), J('ELM-02、ELM-03', 'ELM-02, ELM-03'), J('返却して通知する', 'Returns and notifies'), J('なし', 'none')]],
        'CUJ-04': [[J('レポートを開く', 'Open the report'), 'FR-05', J('ELM-02、ELM-03、ELM-06', 'ELM-02, ELM-03, ELM-06'), J('前の日までのレポート', 'The report up to the previous day'), J('なし', 'none')]],
    }
    cuj_names = {'CUJ-01': J('課題の提出', 'Submit homework'), 'CUJ-02': J('採点と返却', 'Grade and return'),
                 'CUJ-03': J('提出の失敗の調査', 'Investigate a failed submission'), 'CUJ-04': J('月次の提出状況の確認', 'Check monthly submissions')}
    WH = [J('手順', 'Step'), 'FR', J('要素', 'Elements'), J('やり取り', 'Interactions'), J('欠け', 'Gap')]
    walk_md = []
    for cuj in ('CUJ-01', 'CUJ-02', 'CUJ-03', 'CUJ-04'):
        # the Japanese report labels each CUJ with a line ending in a colon, the English one with a line in bold
        walk_md += [J(f'{cuj} {cuj_names[cuj]}:', f'**{cuj} {cuj_names[cuj]}**')]
        if cuj == 'CUJ-03':
            walk_md += ['', J('知らせを受けた開発者が、トレース ID でログをたどり、原因を直す（DEC-05）。手順ごとの表にするほどの手順はない。',
                              'The developer who gets the notice traces the logs with the trace ID and fixes the cause (DEC-05). Too few steps for a table.'), '']
        else:
            walk_md += [table(WH, walk[cuj]), '']

    flows_ctx = J('''flowchart LR
  st["USR-01 生徒"] --> sa["ELM-01"]
  te["USR-02 講師"] --> ta["ELM-02"]
  sa --> api["ELM-03"]
  ta --> api
  sa --> os[["ELM-05 外部のストレージ"]]
  api --> db[("ELM-04 データベース")]
  bat["ELM-06"] --> db''', '''flowchart LR
  st["USR-01 Student"] --> sa["ELM-01"]
  te["USR-02 Teacher"] --> ta["ELM-02"]
  sa --> api["ELM-03"]
  ta --> api
  sa --> os[["ELM-05 External storage"]]
  api --> db[("ELM-04 Database")]
  bat["ELM-06"] --> db''')
    threat = J('''flowchart LR
  subgraph tdev["信頼の境界: 生徒と講師の端末"]
    sa["ELM-01 生徒の Web アプリ"]
    ta["ELM-02 講師の Web アプリ"]
  end
  subgraph tsys["信頼の境界: 塾のクラウド"]
    api["ELM-03 API サーバー"]
    db[("ELM-04 データベース")]
  end
  os[["ELM-05 外部のストレージ"]]
  sa -->|F1 提出、F2 下書き| api
  ta -->|F3 採点と返却| api
  sa -->|F4 ファイル| os
  api -->|F5 署名付き URL| os
  api -->|F6 読み書き| db''', '''flowchart LR
  subgraph tdev["Trust boundary: student and teacher devices"]
    sa["ELM-01 Student web app"]
    ta["ELM-02 Teacher web app"]
  end
  subgraph tsys["Trust boundary: the school's cloud"]
    api["ELM-03 API server"]
    db[("ELM-04 Database")]
  end
  os[["ELM-05 External storage"]]
  sa -->|F1 submission, F2 draft| api
  ta -->|F3 grading and returns| api
  sa -->|F4 file| os
  api -->|F5 signed URL| os
  api -->|F6 reads and writes| db''')
    threat_rows = J([
        ['F1', '端末 → 塾のクラウド', '他人になりすまして提出する: セッション（DEC-01）', '期限を書き換える: サーバーが判定する'],
        ['F2', '端末 → 塾のクラウド', '他人の下書きを読む: 本人だけ（DRV-08）', '—'],
        ['F3', '端末 → 塾のクラウド', '担当でない講師が採点する: 担当を確かめる（FND-02）', '点数を書き換える: 記録を残す'],
        ['F4、F5', '端末と塾のクラウド → 外部サービス', 'URL を盗んで置く: 15 分の期限（DEC-02）', '—'],
        ['F6', '塾のクラウドの中', '—', '—']], [
        ['F1', 'device → school cloud', 'Submitting as someone else: session (DEC-01)', 'Changing the deadline: the server decides'],
        ['F2', 'device → school cloud', "Reading someone else's draft: owner only (DRV-08)", '—'],
        ['F3', 'device → school cloud', 'A teacher who does not teach the class grades: the class is checked (FND-02)', 'Changing a grade: it is recorded'],
        ['F4, F5', 'device and school cloud → external service', 'Uploading with a stolen URL: 15-minute expiry (DEC-02)', '—'],
        ['F6', 'inside the school cloud', '—', '—']])
    r2 = [f'# {J("アーキテクチャ", "Architecture")}: {SYS}', '', status(DAY2, 2), '',
          f'## {J("概要", "Summary")}', '', J('一つの API サーバーと二つの Web アプリ。ファイルはストレージに直接置く。', 'One API server and two web apps; files go straight to the storage.'), '',
          f'## {J("入力", "Inputs")}',
          table([J('出どころ', 'Source'), J('得たもの', 'What it gave')], [['1-architecture-drivers.md', J('設計を動かす要求と順位', 'The drivers and their ranking')]]), '',
          f'## {J("全体の構造", "Overall structure")}', '',
          J('一つの API サーバー（ELM-03）が、二つの Web アプリ（ELM-01、ELM-02）からの要求を受ける。提出のファイルは署名付き URL で外部のストレージ（ELM-05）に直接置く（DEC-02）。',
            'One API server (ELM-03) takes requests from the two web apps (ELM-01, ELM-02). Submitted files go straight to the external storage (ELM-05) through signed URLs (DEC-02).'), '',
          J('DEC-01 システムの分け方:', 'DEC-01 How the system is divided:'),
          table([J('要求（順位）', 'Driver (rank)'), O1[0], O2[0], O3[0]],
                [[J('DRV-01（1）', 'DRV-01 (1)'), J('満たす', 'Meets'), J('満たす', 'Meets'), J('満たす', 'Meets')],
                 [J('DRV-06（5）', 'DRV-06 (5)'), J('満たす', 'Meets'), J('満たさない', 'Fails'), J('一部', 'Partly')]]), '',
          f'## {J("設計の決定", "Design decisions")}', gen('decisions'), '',
          J('DEC-02 ファイルの置き方:', 'DEC-02 How files are stored:'),
          table([J('要求（順位）', 'Driver (rank)'), U1[0], U2[0]], [[J('DRV-01（1）', 'DRV-01 (1)'), J('満たす', 'Meets'), J('満たさない', 'Fails')]]), '',
          f'## {J("設計の観点", "Design concerns")}',
          table([J('観点', 'Concern'), J('決めた決定、後の段階に残すもの、標準のやり方で足りる理由', 'Settled by, left to a later stage, or why standard practice is enough')],
                [[J('並行性', 'Concurrency'), J('同じ提出の送り直しは冪等キーで一つにする（第 3 段階が決める）', 'Retried submissions are made one by idempotency keys (stage 3 decides how)')],
                 [J('データの永続化', 'Data persistence'), J('記録と受領を一つのトランザクションで書く（DEC-03、FND-01 を受けて）', 'The record and the receipt are written in one transaction (DEC-03, after FND-01)')],
                 [J('エラー処理と障害許容', 'Error handling and fault tolerance'), J('ストレージの障害では提出を止め、もう一度試すよう示す', 'On a storage outage, submissions stop and ask to try again')],
                 [J('可変性', 'Variability'), J('保護者の画面は生徒の Web アプリに足す（DEC-06）', "The parents' screens are added to the students' web app (DEC-06)")]]), '',
          f'## {J("脅威のモデル", "Threat model")}', '',
          J('守るもの: 生徒の答案、提出の記録、採点。', "Assets: students' answers, submission records, grades."), '',
          mmd(threat), '',
          table(J(['流れ', '越える境界', 'なりすまし', '改ざん'], ['Flow', 'Crosses', 'Spoofing', 'Tampering']), threat_rows), '',
          f'## {J("要素", "Elements")}', gen('elements'), '',
          f'## {J("ビュー", "Views")}', '',
          f'### {J("外部との関係", "Context")}', '', mmd(flows_ctx), '',
          f'### {J("実行時の構成", "Runtime")}', '',
          mmd(J('flowchart LR\n  sa["ELM-01"] -->|"提出"| api["ELM-03"]\n  api -->|"記録"| db[("ELM-04")]\n  sa -->|"ファイル"| os[["ELM-05"]]',
                'flowchart LR\n  sa["ELM-01"] -->|"submission"| api["ELM-03"]\n  api -->|"record"| db[("ELM-04")]\n  sa -->|"file"| os[["ELM-05"]]')), '',
          table([J('つなぎ', 'Connector'), J('形', 'Style'), J('誰が誰を待つか', 'Who waits for whom')],
                [['ELM-01 → ELM-03', J('要求と応答', 'Request and response'), J('ELM-01 が 10 秒まで', 'ELM-01, up to 10 s')],
                 ['ELM-03 → ELM-04', J('要求と応答', 'Request and response'), J('ELM-03 が 2 秒まで', 'ELM-03, up to 2 s')]]), '',
          f'### {J("配置", "Deployment")}', '',
          mmd(J('flowchart TB\n  subgraph n["ELM-07 クラウドの実行環境"]\n    api["ELM-03"]\n    bat["ELM-06"]\n  end\n  api --> db[("ELM-04")]\n  bat --> db',
                'flowchart TB\n  subgraph n["ELM-07 Cloud runtime"]\n    api["ELM-03"]\n    bat["ELM-06"]\n  end\n  api --> db[("ELM-04")]\n  bat --> db')), '',
          f'### {J("情報", "Information")}', '',
          mmd(J('flowchart LR\n  a["課題（ELM-04）"] --> s["提出（ELM-04）"]\n  s --> f["提出のファイル（ELM-05）"]\n  s --> g["採点（ELM-04）"]',
                'flowchart LR\n  a["Assignment (ELM-04)"] --> s["Submission (ELM-04)"]\n  s --> f["Submitted file (ELM-05)"]\n  s --> g["Grade (ELM-04)"]')), '',
          f'## {J("通し確認", "Walkthroughs")}', '',
          f'### {J("CUJ", "CUJs")}', ''] + walk_md + [
          f'### {J("主な設計を動かす要求", "Primary drivers")}',
          table(['DRV', J('刺激が入る所', 'Where the stimulus enters'), J('応答を形づくる決定', 'Decisions that shape the response'),
                 J('測定量を満たせるか', 'Meets the measure?'), J('残るリスク', 'Remaining risk')],
                [['DRV-01', 'ELM-03', J('DEC-01、DEC-02', 'DEC-01, DEC-02'), J('満たす見込み', 'Likely'), J('ストレージの障害', 'A storage outage')],
                 ['DRV-03', 'ELM-03', 'DEC-03', J('満たす', 'Yes'), J('なし', 'None')],
                 ['DRV-05', 'ELM-01', 'DEC-02', J('満たす', 'Yes'), J('なし', 'None')],
                 ['DRV-02', 'ELM-03', 'DEC-03', J('満たす見込み（第 3 段階の予算）', 'Likely (stage 3 budget)'), J('書き込みの遅れ', 'A slow write')]]), '',
          f'## {J("設計上の値", "Design parameters")}', gen('parameters'), '',
          # DEC-06's debt is left out on purpose: dec/DEC-06.yaml records it
          f'## {J("技術的負債と先送り", "Debt and deferrals")}',
          table([J('項目', 'Item'), J('技術的負債か、確定の種類の先送りか', 'Debt, or deferral of a full-depth kind'), J('決めた所', 'Decided in')],
                [['DEC-04', J('負債: ', 'Debt: ') + decs[3]['debt']['what'], 'DEC-04'],
                 ['HND-02', J('先送り: 保護者の画面の並び', "Deferral: the layout of the parents' screens"), 'DEC-06']]), '',
          f'## {J("費用と体制", "Cost and team")}',
          table([J('費用のもと', 'Cost driver'), J('使う量', 'Usage'), J('値段', 'Price')],
                [[J('実行環境', 'Runtime'), J('一つ、いつも', 'One, always'), J('月 1 万円', '10,000 yen a month')],
                 [J('ストレージ', 'Storage'), J('年 50 GB', '50 GB a year'), J('月 2 千円', '2,000 yen a month')]]), '',
          J('- 2 人で作れる（PC-03）。', '- Two developers can build it (PC-03).'), ''] + closing(
          J('architecture-to-technical-policy を実行する。', 'Run architecture-to-technical-policy.'),
          [['1', J('トレース ID はどこで作るか', 'Where is the trace ID created?'), J('ブラウザ（下書きどおり）', 'The browser (as drafted)'), 'DEC-05']])

    repos = J('flowchart TB\n  root["homework-service"] --> apps["apps/"]\n  apps --> web["web（ELM-01、ELM-02）"]\n  apps --> server["server（ELM-03、ELM-06）"]\n  root --> pkgs["packages/contracts"]\n  web --> pkgs\n  server --> pkgs',
              'flowchart TB\n  root["homework-service"] --> apps["apps/"]\n  apps --> web["web (ELM-01, ELM-02)"]\n  apps --> server["server (ELM-03, ELM-06)"]\n  root --> pkgs["packages/contracts"]\n  web --> pkgs\n  server --> pkgs')
    pipeline = J('flowchart LR\n  pr["変更"] --> check["check: 型、リンター、単体と結合"]\n  check --> main["main"]\n  main --> rel["release: 端から端、イメージ"]\n  rel --> dep["配備"]',
                 'flowchart LR\n  pr["change"] --> check["check: types, linter, unit and integration"]\n  check --> main["main"]\n  main --> rel["release: end-to-end, image"]\n  rel --> dep["deploy"]')
    r2b = [f'# {J("技術方針", "Technical policy")}: {SYS}', '', status(DAY3, '2b'), '',
           f'## {J("概要", "Summary")}', '', J('TypeScript の一つのリポジトリで、Web アプリは React、API サーバーは Hono で書く。', 'One TypeScript repository: React for the web apps, Hono for the API server.'), '',
           f'## {J("入力", "Inputs")}',
           table([J('出どころ', 'Source'), J('得たもの', 'What it gave')], [['2-architecture.md', J('要素と配置', 'Elements and deployment')]]), '',
           f'## {J("すでに決まっていたこと", "What was already decided")}',
           table([J('出どころ', 'Source'), J('決めていること', 'Fixes'), J('従う方針', 'Followed by')],
                 [['TC-01', 'TypeScript', 'POL-01'], ['TC-04', J('Web アプリ', 'Web apps'), 'POL-01']]), '',
           f'## {J("技術方針", "Technical policies")}', gen('policies'), '',
           f'## {J("設計の決定", "Design decisions")}', gen('decisions'), '',
           f'## {J("リポジトリとディレクトリ", "Repositories and directories")}', '',
           '```text\nhomework-service/\n  apps/web/\n  apps/server/\n  packages/contracts/\n```', '', mmd(repos), '',
           f'## {J("パイプライン", "Pipeline")}', '', mmd(pipeline), '',
           f'## {J("ゲートの出どころ", "Gate bindings")}', gen('gate-bindings'), '',
           f'## {J("監査の置き場所", "Audit bindings")}', gen('audit-bindings'), '',
           f'## {J("インタフェースの種類", "Interface kinds")}',
           table([J('インタフェースの種類', 'Kind of interface'), J('現れる所', 'Seen in'), J('仕様書の決め方', 'Spec rule')],
                 [['HTTP', J('IFC-01、IFC-02', 'IFC-01, IFC-02'), J('コードから生成する', 'From code')],
                  [J('ファイル', 'File'), 'IFC-03', J('相手の文書', 'Owner')], [J('バッチ', 'Batch'), 'IFC-04', J('作らない', 'None')]]), ''] + closing(
           J('architecture-to-high-level-design を実行する。', 'Run architecture-to-high-level-design.'),
           [['1', J('Node.js の版の決まりは？', 'Which Node.js versions?'), J('Active LTS の版（下書きどおり）', 'The Active LTS version (as drafted)'), 'DAS-02']])

    hop = J([['ELM-01 が要求を送る', '0.30 秒', '仮'], ['ELM-03 の処理', '0.20 秒', '仮'],
             ['ELM-04 に記録と受領を書く（DEC-03）', '0.50 秒', '仮。書き込みの 99 パーセンタイル'],
             ['ブラウザに戻って示す', '0.50 秒', '仮'], ['余裕', '1.50 秒', ''], ['計', '3.00 秒', 'NFR-06 のしきい値']],
            [['ELM-01 sends the request', '0.30 s', 'Provisional'], ['ELM-03 own work', '0.20 s', 'Provisional'],
             ['Write the record and the receipt in ELM-04 (DEC-03)', '0.50 s', 'Provisional; the 99th percentile of the write'],
             ['Back to the browser and shown', '0.50 s', 'Provisional'], ['Margin', '1.50 s', ''], ['Total', '3.00 s', 'NFR-06 threshold']])
    seq1 = J('''sequenceDiagram
  participant S as USR-01 生徒
  participant A as ELM-01 生徒の Web アプリ
  participant P as ELM-03 API サーバー
  participant O as ELM-05 外部のストレージ
  participant D as ELM-04 データベース
  S->>A: ファイルを添付して提出する
  A->>P: POST /api/v1/uploads
  P-->>A: 署名付き URL（15 分）
  A->>O: 署名付き URL に PUT
  A->>P: POST /api/v1/submissions（冪等キー）
  P->>D: 記録と受領を一つのトランザクションで書く
  alt 締め切りを過ぎた
    P-->>A: 409 DEADLINE_PASSED
  else 書けた
    P-->>A: 201 受領
  end
  A-->>S: 受領を示す''', '''sequenceDiagram
  participant S as USR-01 Student
  participant A as ELM-01 Student web app
  participant P as ELM-03 API server
  participant O as ELM-05 External storage
  participant D as ELM-04 Database
  S->>A: Attach a file and submit
  A->>P: POST /api/v1/uploads
  P-->>A: Signed URL (15 minutes)
  A->>O: PUT to the signed URL
  A->>P: POST /api/v1/submissions (idempotency key)
  P->>D: Write the record and the receipt in one transaction
  alt The deadline has passed
    P-->>A: 409 DEADLINE_PASSED
  else Written
    P-->>A: 201 receipt
  end
  A-->>S: Show the receipt''')
    seq2 = J('''sequenceDiagram
  participant T as USR-02 講師
  participant A as ELM-02 講師の Web アプリ
  participant P as ELM-03 API サーバー
  T->>A: 採点して返却する
  A->>P: PUT /api/v1/teacher/submissions/{id}/grade
  A->>P: POST /api/v1/teacher/submissions/{id}/return
  P-->>A: 返却済み
  A-->>T: 返却を示す''', '''sequenceDiagram
  participant T as USR-02 Teacher
  participant A as ELM-02 Teacher web app
  participant P as ELM-03 API server
  T->>A: Grade and return
  A->>P: PUT /api/v1/teacher/submissions/{id}/grade
  A->>P: POST /api/v1/teacher/submissions/{id}/return
  P-->>A: Returned
  A-->>T: Show that it is returned''')
    seq3 = J('''sequenceDiagram
  participant A as ELM-01 生徒の Web アプリ
  participant P as ELM-03 API サーバー
  participant O as ELM-05 外部のストレージ
  Note over A,O: 締め切り前の集中: ファイルはサーバーを通らない
  A->>O: 署名付き URL に PUT
  A->>P: POST /api/v1/submissions''', '''sequenceDiagram
  participant A as ELM-01 Student web app
  participant P as ELM-03 API server
  participant O as ELM-05 External storage
  Note over A,O: The deadline rush: files never pass through the server
  A->>O: PUT to the signed URL
  A->>P: POST /api/v1/submissions''')
    screens1 = J('flowchart LR\n  list["課題の一覧"] --> as["課題"]\n  as --> at["ファイルの添付"]\n  at --> conf["提出の確認"]\n  conf --> rc["受領"]\n  conf -.->|"締め切りを過ぎた"| late["締め切りの表示"]',
                 'flowchart LR\n  list["Assignments"] --> as["Assignment"]\n  as --> at["Attach a file"]\n  at --> conf["Confirm"]\n  conf --> rc["Receipt"]\n  conf -.->|"deadline passed"| late["Deadline message"]')
    screens2 = J('flowchart LR\n  sl["提出の一覧"] --> sd["提出"]\n  sd --> gr["採点"]\n  gr --> rt["返却"]',
                 'flowchart LR\n  sl["Submissions"] --> sd["Submission"]\n  sd --> gr["Grade"]\n  gr --> rt["Return"]')
    er = 'erDiagram\n  DAT-01 ||--o{ DAT-02 : "' + J('提出', 'submits') + '"\n  DAT-02 ||--|| DAT-03 : "' + J('ファイル', 'file') + '"\n  DAT-02 ||--o| DAT-04 : "' + J('採点', 'grade') + '"'
    states = J('stateDiagram-v2\n  [*] --> draft: 下書きを保存\n  draft --> submitted: 提出（記録と受領）\n  submitted --> graded: 採点\n  graded --> returned: 返却\n  returned --> [*]',
               'stateDiagram-v2\n  [*] --> draft: save the draft\n  draft --> submitted: submit (record and receipt)\n  submitted --> graded: grade\n  graded --> returned: return\n  returned --> [*]')
    dq = J('flowchart LR\n  s["提出（DAT-02）"] --> r["夜間のバッチ（ELM-06）"]\n  r --> m["月次のレポート"]',
           'flowchart LR\n  s["Submission (DAT-02)"] --> r["Nightly batch (ELM-06)"]\n  r --> m["Monthly report"]')
    r3 = [f'# {J("概略設計", "High-level design")}: {SYS}', '', status(DAY4, 3), '',
          f'## {J("概要", "Summary")}', '', J('インタフェースは四つ。確定の予算は 3 秒に収まる。', 'Four interfaces; the confirmation budget fits in 3 seconds.'), '',
          f'## {J("入力", "Inputs")}',
          table([J('出どころ', 'Source'), J('得たもの', 'What it gave')], [['2b-technical-policy.md', J('技術方針', 'The technical policies')]]), '',
          f'## {J("共通の約束事", "Shared conventions")}',
          table([J('約束事', 'Convention'), 'DEC'],
                [[J('エラーは問題の詳細に code と traceId を足して返す', 'Errors are problem details with a code and a traceId'), 'DEC-09'],
                 [J('状態を変える要求すべてに Idempotency-Key', 'An Idempotency-Key on every state-changing request'), 'DEC-10']]), '',
          f'## {J("設計の決定", "Design decisions")}', gen('decisions'), '',
          f'## {J("インタフェース", "Interfaces")}', gen('interfaces'), '',
          f'## {J("SLI の出どころ", "SLI bindings")}', gen('sli-bindings'), '',
          f'## {J("端から端の流れ", "End-to-end flows")}', '',
          f'### CUJ-01 {cuj_names["CUJ-01"]}', '', mmd(seq1), '',
          f'### CUJ-02 {cuj_names["CUJ-02"]}', '', mmd(seq2), '',
          f'### DRV-01 {drvs[0]["title"]}', '', mmd(seq3), '',
          f'## {J("遅延の予算とタイムアウト", "Latency budgets and timeouts")}', '',
          f'### NFR-06{J("（SLI-01）", " (SLI-01)")}', '',
          J('測る区間は、ブラウザが送ってから受領を示すまで。', 'Measured from the browser sending the request to the receipt being shown.'), '',
          table([J('ホップ（送ってから受領を示すまで）', 'Hop'), J('予算（99 パーセンタイル、4 ホップ）', 'Budget (99th percentile, 4 hops)'), J('もと', 'Basis')], hop), '',
          J('失敗したときの流れとエラーバジェット: ストレージの障害の間の失敗は NFR-01 のバジェットに入る。', "Failure paths and the error budget: failures during a storage outage count against NFR-01's budget."), '',
          f'### NFR-02{J("（SLI-02）", " (SLI-02)")}', '',
          J('02:00 に起動し、4 時間の余裕がある（DEC-04）。ホップの表にするほどのホップはない。',
            'It starts at 02:00, with four hours to spare (DEC-04). Too few hops for a table.'), '',
          f'### {J("タイムアウト", "Timeouts")}',
          table([J('呼び出しの道', 'Call path'), J('値（IFC）', 'Value (IFC)'), J('呼ぶ側が待つ最悪', 'Worst wait of the caller')],
                [['ELM-01 → ELM-03', J('10 秒（IFC-01）', '10 s (IFC-01)'), J('10 秒', '10 s')]]), '',
          f'## {J("画面", "Screens")}', '',
          f'### CUJ-01 {cuj_names["CUJ-01"]}', '', mmd(screens1), '',
          f'### CUJ-02 {cuj_names["CUJ-02"]}', '', mmd(screens2), '',
          f'## {J("データ", "Data")}', '', mmd(er), '', gen('data'), '',
          f'### {J("データの品質の流れ", "Data quality flows")}',
          table([J('要求', 'Requirement'), J('どこから来るか', 'Comes from'), J('どう確かめるか', 'Checked by'), J('どう伝わり、どれだけかかるか', 'Passed on by, and how long it takes'),
                 J('何と照らし合わせるか', 'Compared with')],
                [['QR-07', 'ELM-03', J('毎晩、受領と記録を照らす', 'Receipts against records every night'), J('ELM-06、翌朝まで', 'ELM-06, by the next morning'), J('受領と記録', 'Receipts and records')]]), '',
          mmd(dq), '',
          f'## {J("要素をまたぐ状態", "States across elements")}', '',
          f'### {J("提出（DAT-02）", "Submission (DAT-02)")}', '', mmd(states), '',
          J('submitted になるのは記録を書いた後だけ（DRV-09）。', 'It becomes submitted only after the record is written (DRV-09).'), '',
          f'## {J("受け入れ基準のたどり", "Acceptance criteria trace")}', gen('criteria'), ''] + closing(
          J('high-level-design-to-detailed-design を、コンポーネントごとに実行する。', 'Run high-level-design-to-detailed-design for each component.'),
          [['1', J('エラーの形は？', 'Which error shape?'), J('問題の詳細（下書きどおり）', 'Problem details (as drafted)'), 'DEC-09']])

    files = {'design-context.yaml': ctx}
    stage3 = {'DEC-09', 'DEC-10', 'HND-03', 'QCR-01'}
    stage2b = {'DEC-07', 'DEC-08', 'HND-04', 'DAS-02'}
    for coll, sub in ((drvs, 'drv'), (decs, 'dec'), (elms, 'elm'), (fnds, 'fnd'), (hnds, 'hnd'), (dases, 'das'), (qcrs, 'qcr')):
        for d in coll:
            if not full and d['id'] in stage3 | stage2b:
                continue
            files[f'{sub}/{d["id"]}.yaml'] = d
    files['reviews/2-architecture.md'] = '\n'.join([
        f'# {J("設計のレビュー: 第 2 段階", "Design review: stage 2")} {J("の", "of")} {SYS}', '',
        J(f'状態: 回答反映済み · 更新: {DAY2} · 入力の基準: なし · レビュー: 全体', f'Status: answers applied · Updated: {DAY2} · Inputs as of: none · Review: full'), '',
        f'## {J("概要", "Summary")}', '', J('指摘 2 件（中 1、軽微 1）。', 'Two findings (one major, one minor).'), ''])
    files['1-architecture-drivers.md'] = '\n'.join(r1)
    files['2-architecture.md'] = '\n'.join(r2)
    if full:
        for coll, sub in ((pols, 'pol'), (ifcs, 'ifc'), (dats, 'dat')):
            for d in coll:
                files[f'{sub}/{d["id"]}.yaml'] = d
        files['2b-technical-policy.md'] = '\n'.join(r2b)
        files['3-high-level-design.md'] = '\n'.join(r3)
    # the cells of generated tables that the reports fill in by hand
    hand = {
        'design-context': {k: v for k, v in labels.items()},
        'conflicts': {J('DRV-01、DRV-02', 'DRV-01, DRV-02'): J('第 2 段階（DEC-03）', 'Stage 2 (DEC-03)')},
        'parameters': {d['parameters'][0]['name']: d['id'] for d in decs if d['parameters'] and d['stage'] == 'architecture'},
        'criteria': {'FR-01': 'CUJ-01', 'FR-02': 'CUJ-01', 'FR-03': 'CUJ-02', 'FR-04': 'CUJ-03', 'FR-05': 'CUJ-04',
                     'FR-06': 'CUJ-01', 'FR-08': 'CUJ-02', 'FR-09': 'CUJ-04'},
        'assumptions': J('低', 'Low'),
    }
    return files, hand


def req_to_design():
    base = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('REQ_TO_DESIGN', ROOT.parent / 'req-to-design'))
    scripts = base / 'shared' / 'scripts'
    if not (scripts / 'tables.py').is_file():
        sys.exit('req-to-design の scripts/tables.py が見つからない: %s。場所を引数か REQ_TO_DESIGN で渡す' % scripts)
    return scripts


def run(script, design, quality, *extra):
    return subprocess.run([sys.executable, str(script), '--design', str(design), '--quality', str(quality)] + list(extra),
                          capture_output=True, text=True)


GEN_RE = re.compile(r'(<!--\s*generated:\s*([A-Za-z0-9_-]+)\s*-->\n)(.*?)(\n<!--\s*/generated\s*-->)', re.S)


def fill_hand_cells(design, hand):
    """Fills the cells of the generated tables that a report writes by hand and tables.py leaves empty"""
    for p in sorted(design.glob('*.md')):
        text = p.read_text(encoding='utf-8')

        def fill(m):
            name, body = m.group(2), m.group(3)
            lines = body.split('\n')
            out = []
            for k, line in enumerate(lines):
                if k < 2 or not line.startswith('|'):
                    out.append(line)
                    continue
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                if name in ('design-context', 'conflicts') and len(cells) > 1 and not cells[1]:
                    cells[1] = hand[name].get(cells[0], '—')
                elif name == 'parameters' and len(cells) == 3 and not cells[2]:
                    cells[2] = hand['parameters'].get(cells[0], cells[1])
                elif name == 'criteria' and len(cells) == 4 and not cells[3]:
                    cells[3] = hand['criteria'].get(cells[0], '—')
                elif name == 'assumptions' and len(cells) == 6 and cells[0].startswith('QAS-'):
                    cells[3] = cells[3] or hand['assumptions']
                    cells[4] = cells[4] or hand['assumptions']
                out.append('| ' + ' | '.join(cells) + ' |')
            return m.group(1) + '\n'.join(out) + m.group(4)
        p.write_text(GEN_RE.sub(fill, text), encoding='utf-8')


def write(case, lang, quality_case, upto, scripts):
    base = EVALS / case / 'files' / 'docs'
    if base.exists():
        shutil.rmtree(base)
    d = base / 'design'
    files, hand = data(lang, upto)
    for path, content in sorted(files.items()):
        p = d / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            p.write_text(content, encoding='utf-8')
        else:
            p.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False, width=1000), encoding='utf-8')
    q = base / 'quality'
    shutil.copytree(QUALITY / quality_case / 'files' / 'docs' / 'quality', q, ignore=shutil.ignore_patterns('summary.html'))
    # the generated tables, as every stage writes them before it commits, then the cells written by hand
    for step in ('write', 'fill', 'write'):
        if step == 'fill':
            fill_hand_cells(d, hand)
            continue
        r = run(scripts / 'tables.py', d, q)
        if r.returncode not in (0, 1):
            sys.exit('tables.py が失敗した（%s）:\n%s%s' % (case, r.stdout, r.stderr))
    r = run(scripts / 'tables.py', d, q, '--dry-run')
    stale = r.stdout.strip() if r.returncode else ''
    c = run(scripts / 'check.py', d, q)
    print(f'書いた: {base.relative_to(ROOT)}')
    if stale:
        print('  tables.py --dry-run が書き直す表がある:\n' + stale)
    if c.returncode:
        print('  check.py の問題:\n' + '\n'.join('    ' + x for x in c.stdout.strip().splitlines()))
    else:
        print('  check.py: 問題なし')


if __name__ == '__main__':
    s = req_to_design()
    write('homework-service-full', 'ja', 'homework-service-full', '3', s)
    write('homework-service-full-en', 'en', 'homework-service-full-en', '3', s)
    write('homework-service-stage2', 'ja', 'homework-service-full', '2', s)

#!/usr/bin/env python3
"""Build the design outputs (docs/design) of the fictional homework submission service (課題提出サービス) for
design-summary-html's evals, on top of the quality outputs in quality-summary-html's evals.

  uv run --with pyyaml python3 tests/make_homework_design_fixture.py

Writes to these directories under skills/design-summary-html/evals/:
  homework-service-full/files/docs      stages 1 to 3 of the design, in Japanese, and docs/quality
  homework-service-full-en/files/docs   the same items and reports, in English
  homework-service-stage2/files/docs    stages 1 and 2 only, in Japanese
docs/quality is copied from skills/quality-summary-html/evals/homework-service-full(-en)/files/docs/quality.

Planted on purpose, so that the evals can check the skill notices them:
- the stage 2 report's decisions table leaves out DEC-06 (added to the YAML after the report was written);
- revision notes in YAML texts and report cells (finding numbers, 「DRV-03 版 2」 / "DRV-03 version 2", a sentence about
  the previous version, a sentence about a re-run);
- a retired driver (DRV-10), a CUJ walkthrough written as prose (CUJ-03), a latency budget without a table (NFR-02),
  common error contracts shared by two interfaces, and a hop table that the page draws as a chart (NFR-06);
- texts with more than one sentence and bracketed asides, which the page cuts to their gist (DEC-02's rationale,
  ELM-01's and ELM-02's responsibilities, DAT-02's consistency).
"""
import pathlib
import shutil

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVALS = ROOT / 'skills' / 'design-summary-html' / 'evals'
QUALITY = ROOT / 'skills' / 'quality-summary-html' / 'evals'
DAY1, DAY2, DAY3, DAY4 = '2026-09-15', '2026-09-18', '2026-09-22', '2026-09-25'


def data(lang):
    """Every item and report of the fictional design, in Japanese (ja) or English (en)"""
    def J(ja, en):
        return ja if lang == 'ja' else en

    def common(i, title, day, reason, agree=False, version=1, more_log=()):
        d = {'id': i, 'title': title, 'status': 'draft', 'version': version, 'basis': 'inferred', 'basis_note': None,
             'needs_agreement': agree, 'approver_candidates': [J('プロダクトオーナー', 'Product owner')] if agree else []}
        log = [{'version': 1, 'date': day, 'change': J('作成', 'Created'), 'reason': reason}] + list(more_log)
        return d, log

    def item(i, title, day, reason, fields, **kw):
        d, log = common(i, title, day, reason, **kw)
        d.update(fields)
        d['changelog'] = log
        return d

    S1 = J('第 1 段階の下書き', 'Stage 1 draft')
    S2 = J('第 2 段階の下書き', 'Stage 2 draft')
    S3 = J('第 3 段階の下書き', 'Stage 3 draft')
    SYS = J('課題提出サービス', 'Homework submission service')

    # ---------------- design-context.yaml
    ctx = {
        'read_from': {'quality_chain': 'docs/quality/', 'other': [J('利用者の入力（2026-09-15）', 'User input (2026-09-15)')]},
        'technology_constraints': [
            {'id': 'TC-01', 'statement': J('TypeScript で書く', 'Written in TypeScript'), 'kind': 'mandated',
             'source': J('利用者の入力', 'User input'), 'basis': 'stated'},
            {'id': 'TC-02', 'statement': J('提出したファイルは外部のストレージ（ObjectStore）に置く',
                                           'Submitted files are kept in an external storage service (ObjectStore)'),
             'kind': 'external-service', 'source': J('context.yaml の制約', 'context.yaml constraints'), 'basis': 'stated'},
            {'id': 'TC-03', 'statement': J('塾の既存のクラウドの一つの地域で動かす', "Runs in one region of the school's existing cloud account"),
             'kind': 'platform', 'source': J('利用者の入力、質問 2', 'User input, question 2'), 'basis': 'confirmed'},
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
        'as_is': None,
    }

    # ---------------- drivers
    def drv(i, title, kind, statement, sources, rank=None, business='high', breason='', difficulty='medium', dreason='',
            primary=False, scenario=None, negotiable=None, derived=(), conflicts=(), agree=True, status='draft'):
        d = item(i, title, DAY1, S1, {
            'kind': kind, 'statement': statement, 'sources': list(sources), 'concern_of': ['USR-01'] if kind == 'quality' else [],
            'scenario': scenario, 'negotiable': negotiable, 'derived_from': list(derived),
            'priority': None if kind == 'principle' else {'business': business, 'business_reason': breason,
                                                          'difficulty': difficulty, 'difficulty_reason': dreason, 'rank': rank},
            'primary': primary, 'conflicts': [{'with': w, 'note': n} for w, n in conflicts], 'placeholders': []}, agree=agree)
        d['status'] = status
        return d

    def scen(source, stimulus, artifact, environment, response, measure):
        return {'source': source, 'stimulus': stimulus, 'artifact': artifact, 'environment': environment,
                'response': response, 'measure': measure}

    drvs = [
        drv('DRV-01', J('締め切り前の集中でも提出を受け付け続ける', 'Keep accepting submissions in the rush before a deadline'), 'quality',
            J('締め切り前の 1 時間に提出が集中しても、提出を受け付け続ける', 'Keep accepting submissions even when they peak in the hour before a deadline'),
            ['QR-01', 'NFR-01', 'SLI-01', 'TC-02'], 1, 'high', J('QR-01 が重視（CUJ-01）', 'QR-01 is emphasized (CUJ-01)'),
            'high', J('提出が締め切り前に集中し、外部のストレージに頼る', 'Submissions peak before deadlines and rely on the external storage'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('締め切り前の 1 時間に提出する', 'Submit in the hour before a deadline'), 'FR-01',
                 J('締め切り前の集中（1 分に 300 件）', 'The rush before a deadline (300 submissions a minute)'),
                 J('提出が受け付けられ、受領が示される', 'The submission is accepted and the receipt is shown'),
                 J('直近 28 日で、有効な提出の 99.5% が成功する（NFR-01）', '99.5% of valid submissions succeed over a rolling 28 days (NFR-01)')),
            conflicts=[('DRV-02', J('受領の前に記録を書くと、確定が遅くなる', 'Writing the record before the receipt slows the confirmation'))]),
        drv('DRV-02', J('提出の確定を待たせない', 'Confirm submissions without keeping students waiting'), 'quality',
            J('提出の確定を 3 秒以内に返す', 'Return the confirmation of a submission within 3 seconds'),
            ['QR-02', 'NFR-06'], 4, 'medium', J('QR-02 は最低限守る線', 'QR-02 is a minimum line'),
            'medium', J('記録を先に書く分だけ遅くなる（DRV-09）', 'Writing the record first adds time (DRV-09)'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('提出する', 'Submit'), 'FR-01, FR-02',
                 J('締め切り前の集中', 'The rush before a deadline'), J('受領が示される', 'The receipt is shown'),
                 J('提出の確定の 95 パーセンタイルが 3 秒以内（NFR-06）', 'The 95th percentile of submission confirmation is within 3 seconds (NFR-06)')),
            conflicts=[('DRV-01', J('受領の前に記録を書くと、確定が遅くなる（FND-01）', 'Writing the record before the receipt slows the confirmation (FND-01)'))]),
        drv('DRV-03', J('受領の表示が提出の記録と一致する', 'Receipts match the submission records'), 'quality',
            J('受領を示した提出は、必ず記録に残っている', 'Every submission whose receipt is shown is in the records'),
            ['QR-03', 'QR-07', 'NFR-03', 'NFR-07'], 2, 'high', J('QR-03 と QR-07 が重視（CUJ-01、04）', 'QR-03 and QR-07 are emphasized (CUJ-01, 04)'),
            'medium', J('ファイルの置き場所と記録の置き場所が別', 'The files and the records are kept in different places'), True,
            scen(J('生徒（USR-01）', 'Students (USR-01)'), J('提出する', 'Submit'), 'FR-02',
                 J('ふだんと締め切り前の集中', 'Normal operation and the rush before a deadline'),
                 J('受領と記録が一致する', 'The receipt matches the record'),
                 J('受領と記録の食い違いが 0 件（NFR-07 版 2）', 'No receipt without a record (NFR-07 version 2)'))),
        drv('DRV-04', J('保護者向けの画面を足せる', "Screens for parents can be added"), 'change',
            J('保護者向けの画面を、今の画面と API を変えずに足せる', "Parents' screens can be added without changing the existing screens and APIs"),
            ['CHG-01'], 6, 'medium', J('将来の変更（CHG-01）', 'An anticipated change (CHG-01)'),
            'low', J('役割を足すだけで済む見込み', 'Adding a role is expected to be enough'), False,
            scen(J('開発チーム', 'Development team'), J('保護者の画面を足す', "Add the parents' screens"),
                 J('Web アプリと API', 'The web apps and the API'), J('リリースの後', 'After release'),
                 J('今の画面と API を変えずに足せる', 'Added without changing the existing screens and APIs'),
                 J('2 人で 4 週間以内', 'Within 4 weeks for two developers'))),
        drv('DRV-05', J('提出したファイルは外部のストレージに置く', 'Submitted files are kept in the external storage'), 'constraint',
            J('提出したファイルは外部のストレージ（ObjectStore）に置き、サーバーには置かない', 'Submitted files go to the external storage (ObjectStore), never to our servers'),
            ['TC-02'], 3, 'high', J('交渉できない制約', 'A non-negotiable constraint'),
            'medium', J('ストレージの障害で提出が止まりうる', 'A storage outage can stop submissions'), True, negotiable=False),
        drv('DRV-06', J('2 人で、月 3 万円以内で作って動かす', 'Built and run by two developers within 30,000 yen a month'), 'constraint',
            J('開発者 2 人が作って動かし、走る費用は月 3 万円以内', 'Two developers build and run it, for at most 30,000 yen a month'),
            ['PC-01', 'PC-03'], 5, 'high', J('交渉できない制約', 'A non-negotiable constraint'),
            'low', J('構成を小さく保てば満たせる', 'Met by keeping the structure small'), False, negotiable=False),
        drv('DRV-07', J('一つのトレース ID で提出の失敗をたどる', 'Trace a failed submission with one trace ID'), 'observability',
            J('提出の失敗を、ブラウザからストレージまで一つのトレース ID でたどれる', 'A failed submission can be traced from the browser to the storage with one trace ID'),
            ['QR-10', 'FR-04', 'NFR-09'], 7, 'medium', J('QR-10 は最低限守る線', 'QR-10 is a minimum line'),
            'low', J('ログの欄をそろえれば済む', 'Consistent log fields are enough'), False),
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
    def dec(i, stage, title, day, reason, question, addresses, options, chosen, rationale, rejected, gains=(), costs=(),
            sensitive=(), trade_offs=(), assumptions=(), depends=(), parameters=(), debt=None, deferred=False, revisit=None,
            agree=False, version=1, more_log=()):
        return item(i, title, day, reason, {
            'stage': stage, 'question': question, 'addresses': list(addresses),
            'options': [{'name': n, 'effect': e, 'cost': c} for n, e, c in options],
            'chosen': chosen, 'rationale': rationale, 'rejected': [{'option': o, 'reason': r} for o, r in rejected],
            'gains': list(gains), 'costs': list(costs), 'sensitive_points': list(sensitive),
            'trade_offs': [{'with': w, 'note': n} for w, n in trade_offs], 'assumptions': list(assumptions),
            'depends_on': list(depends), 'parameters': [{'name': n, 'value': v, 'basis': b} for n, v, b in parameters],
            'debt': debt, 'deferred': deferred, 'revisit_when': revisit, 'as_is': 'new'},
            agree=agree, version=version, more_log=more_log)

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
    P2 = (J('生徒の Web アプリに役割を足す', "A parent role in the students' web app"), J('配備するものが増えない', 'Nothing more to deploy'),
          J('生徒の画面の変更と重なる', "Changes overlap with the students' screens"))
    E1 = (J('問題の詳細（RFC 9457）に code と traceId を足す', 'Problem details (RFC 9457) with a code and a traceId'),
          J('標準の形で、道具が使える', 'A standard shape that tools understand'), J('欄が少し増える', 'A few more fields'))
    E2 = (J('独自の {code, message}', 'Our own {code, message}'), J('作りが単純', 'Simple to build'), J('道具の助けを失う', 'No help from tools'))
    K1 = (J('状態を変える要求すべてに冪等キー', 'An idempotency key on every state-changing request'),
          J('送り直しても二重にならない', 'Retries never duplicate'), J('キーを 24 時間持つ', 'Keys are kept for 24 hours'))
    K2 = (J('提出だけに冪等キー', 'An idempotency key on submissions only'), J('持つものが少ない', 'Less to keep'),
          J('返却の送り直しで通知が二重になる', 'A retried return sends two notifications'))
    rerun = [{'version': 2, 'date': DAY4, 'change': J('理由を足した', 'Added to the rationale'),
              'reason': J('第 2 段階の再実行（FND-02）', 'Stage 2 re-run (FND-02)')}]
    decs = [
        dec('DEC-01', 'architecture', J('一つの API サーバーと二つの Web アプリにする', 'One API server and two web apps'), DAY2, S2,
            J('システムをどう分け、どこで動かすか', 'How is the system divided, and where does it run?'),
            ['DRV-06', 'DRV-01', 'DRV-04'], [O1, O2, O3], O1[0],
            J('上位の DRV-01 はどの案でも満たせ、DRV-06（2 人と費用）で一つのサーバーの案が勝つ。',
              'All options meet DRV-01; DRV-06 (two developers, the cost) decides for one server.'),
            [(O2[0], J('2 人では動かせない（DRV-06）', 'Two developers cannot run it (DRV-06)')),
             (O3[0], J('手元で同じ形にならない', 'Does not run the same way locally'))],
            gains=[J('配備するものが一つで済む', 'One thing to deploy')], costs=[J('一つの障害の単位になる', 'A single unit of failure')],
            sensitive=[J('サーバーのインスタンスの数', 'The number of server instances')],
            trade_offs=[('DRV-01', J('締め切り前の集中を一つのサーバーで受ける', 'One server takes the rush before deadlines'))],
            assumptions=[J('同時に使う生徒は 300 人まで', 'At most 300 students at once')]),
        dec('DEC-02', 'architecture', J('提出のファイルを署名付き URL でストレージに直接置く', 'Upload files straight to the storage with signed URLs'), DAY2, S2,
            J('提出のファイルを、サーバーを通さずにどう置くか', 'How are submitted files stored without passing through the server?'),
            ['DRV-01', 'DRV-05', 'DRV-02'], [U1, U2], U1[0],
            J('締め切り前の集中（DRV-01）で、サーバーがファイルを受けると詰まる。署名付き URL なら、ファイルはサーバーを通らない。',
              'In the rush before a deadline (DRV-01), a server receiving the files would choke. With signed URLs, files never pass through the server.'),
            [(U2[0], J('締め切り前に詰まる（DRV-01）', 'Chokes before deadlines (DRV-01)'))],
            gains=[J('締め切り前もファイルでサーバーの負荷が増えない', 'Files add no server load, even before deadlines')],
            costs=[J('URL の期限切れを扱う', 'Expired URLs must be handled')],
            sensitive=[J('署名付き URL の有効期限', "The signed URL's expiry")],
            trade_offs=[('DRV-08', J('URL を持つ人は期限まで置ける', 'Anyone holding the URL can upload until it expires'))],
            depends=['DEC-01'],
            parameters=[(J('署名付き URL の有効期限', 'Signed URL expiry'), J('15 分', '15 minutes'),
                         J('仮。提出の画面を開いてから送るまでの時間', 'Provisional; the time from opening the screen to submitting'))]),
        dec('DEC-03', 'architecture', J('記録を書いてから受領を示す', 'Write the record before showing the receipt'), DAY2, S2,
            J('受領の表示を、提出の記録とどう一致させるか', 'How do receipts stay in line with the submission records?'),
            ['DRV-03', 'DRV-09'], [R1, R2], R1[0],
            J('原則 DRV-09 に従う。前の版は、受領を先に示していた（FND-01）。',
              'It follows principle DRV-09. The previous version showed the receipt first (FND-01).'),
            [(R2[0], J('記録が欠けうる（DRV-03 版 2）', 'Records can go missing (DRV-03 version 2)'))],
            gains=[J('受領が出たら必ず記録がある', 'A receipt always has a record')],
            costs=[J('確定に書き込みの時間が乗る（DRV-02）', 'The write adds to the confirmation time (DRV-02)')],
            sensitive=[J('記録の書き込みの時間', 'The time the write takes')],
            trade_offs=[('DRV-02', J('書き込みの分だけ確定が遅くなる', 'Confirmation is slower by the write'))],
            depends=['DEC-01']),
        dec('DEC-04', 'architecture', J('夜間のレポートをバッチで作る', 'Build the nightly report in a batch'), DAY2, S2,
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
                  'repay_when': J('当日の数字が要ると言われたとき', 'When same-day numbers are asked for')}, agree=True),
        dec('DEC-05', 'architecture', J('トレース ID をブラウザで作って引き継ぐ', 'The browser creates the trace ID and passes it on'), DAY2, S2,
            J('一つの提出の記録をどうつなぐか', 'How are the records of one submission linked?'),
            ['DRV-07'], [T1, T2], T1[0],
            J('2 回目の再実行で足した。CUJ-03 の調べを一つの ID から始められる。',
              'Added in the second re-run. A CUJ-03 investigation starts from one ID.'),
            [(T2[0], J('ブラウザの失敗がつながらない（質問 4、FND-02）', 'Browser failures are not linked (question 4, FND-02)'))],
            gains=[J('通知から原因まで一つの ID でたどれる', 'One ID from the notice to the cause')],
            costs=[J('ログの欄をそろえる', 'Log fields must be consistent')], depends=['DEC-01'], version=2, more_log=rerun),
        dec('DEC-06', 'architecture', J('保護者向けの画面の作り', "How to build the parents' screens"), DAY4,
            J('第 2 段階の再実行', 'Stage 2 re-run'),
            J('保護者向けの画面を、どの Web アプリにどう足すか', "Which web app gets the parents' screens, and how?"),
            ['DRV-04'], [P1, P2], None,
            J('保護者の画面を作るかが、まだ決まっていない（CHG-01）。', "Whether to build the parents' screens is not decided yet (CHG-01)."),
            [], deferred=True, revisit=J('保護者の画面を作ると決めたとき', "When the parents' screens are decided on"), agree=True),
        dec('DEC-07', 'high-level-design', J('エラーを問題の詳細の形で返す', 'Return errors as problem details'), DAY3, S3,
            J('すべての API で、エラーをどの形で返すか', 'In which shape do all APIs return errors?'),
            ['IFC-01', 'IFC-02'], [E1, E2], E1[0],
            J('標準の形にすると、画面と道具が同じ読み方をできる。', 'A standard shape lets the screens and the tools read errors the same way.'),
            [(E2[0], J('道具の助けを失う', 'No help from tools'))]),
        dec('DEC-08', 'high-level-design', J('状態を変える要求に冪等キーを求める', 'State-changing requests carry an idempotency key'), DAY3, S3,
            J('どの要求を冪等にするか', 'Which requests are idempotent?'),
            ['IFC-01', 'IFC-02', 'DRV-03'], [K1, K2], K1[0],
            J('提出も返却も、送り直しで二重にしない（DRV-03）。', 'Neither a submission nor a return may happen twice when retried (DRV-03).'),
            [(K2[0], J('返却が二重になる', 'Returns can happen twice'))],
            parameters=[(J('冪等キーの保持', 'Idempotency key retention'), J('24 時間', '24 hours'), J('仮', 'Provisional'))]),
    ]

    # ---------------- elements
    def elm(i, name, kind, resp, functions, drivers, team='TEAM-01', runs_on='ELM-07', depends=()):
        return item(i, name, DAY2, S2, {'kind': kind, 'name': name, 'responsibility': resp, 'functions': list(functions),
                                        'drivers': list(drivers), 'decisions': [], 'team': team,
                                        'technology': None, 'runs_on': runs_on, 'depends_on': list(depends), 'as_is': 'new'})
    elms = [
        elm('ELM-01', J('生徒の Web アプリ', 'Student web app'), 'component',
            J('課題を開き、ファイルをストレージに直接置き、提出して受領を示す。下書きを保存する',
              'Opens assignments, uploads files straight to the storage, submits and shows receipts. Saves drafts'),
            ['FR-01', 'FR-02', 'FR-06'], ['DRV-01', 'DRV-02', 'DRV-03'], depends=['ELM-03', 'ELM-05']),
        elm('ELM-02', J('講師の Web アプリ', 'Teacher web app'), 'component',
            J('提出を開き、採点して返却する。月次のレポートを見る', 'Opens submissions, grades and returns them. Shows the monthly report'),
            ['FR-03', 'FR-05', 'FR-08'], ['DRV-08'], depends=['ELM-03']),
        elm('ELM-03', J('API サーバー', 'API server'), 'component',
            J('提出の確定と受領、署名付き URL、採点と返却、トレース ID の記録', 'Confirms submissions and receipts, issues signed URLs, grading and returns, records trace IDs'),
            ['FR-01', 'FR-02', 'FR-03', 'FR-04', 'FR-06', 'FR-08'], ['DRV-01', 'DRV-02', 'DRV-03', 'DRV-07', 'DRV-08'],
            depends=['ELM-04', 'ELM-05']),
        elm('ELM-04', J('データベース', 'Database'), 'data-store', J('課題、提出の記録、採点を持つ', 'Holds assignments, submission records and grades'),
            [], ['DRV-03']),
        elm('ELM-05', J('外部のストレージ', 'External storage'), 'external-system', J('提出のファイルを置く（ObjectStore）', 'Keeps the submitted files (ObjectStore)'),
            [], ['DRV-05'], team=None, runs_on=None),
        elm('ELM-06', J('夜間のバッチ', 'Nightly batch'), 'component', J('毎晩、提出状況のレポートを作る', 'Builds the submission report every night'),
            ['FR-05'], ['DRV-06'], depends=['ELM-04']),
        elm('ELM-07', J('クラウドの実行環境', 'Cloud runtime'), 'node', J('API サーバーと夜間のバッチを動かす', 'Runs the API server and the nightly batch'),
            [], [], runs_on=None),
    ]

    # ---------------- interfaces
    def ifc(i, name, kind, provider, consumers, functions, operations, errors, spec=None):
        return item(i, name, DAY3, S3, {
            'kind': kind, 'name': name, 'provider': provider, 'consumers': list(consumers), 'functions': list(functions),
            'operations': [{'name': n, 'does': d} for n, d in operations], 'format': 'JSON', 'protocol': 'HTTPS',
            'auth': J('セッションのクッキー', 'Session cookie'),
            'errors': [{'case': c, 'signal': s, 'caller_does': d} for c, s, d in errors],
            'idempotency': J('状態を変える要求は Idempotency-Key（DEC-08）', 'State-changing requests carry an Idempotency-Key (DEC-08)'),
            'timing': {'timeout': J('ブラウザ 10 秒', 'Browser 10 s'), 'ordering': None, 'delivery': None},
            'versioning': J('経路に v1', 'v1 in the path'), 'observability': J('トレース ID をログに書く', 'Trace IDs in the logs'),
            'spec': spec, 'as_is': 'new'})
    common_errors = [
        (J('共通: ログインしていない', 'Common: not signed in'), '401 UNAUTHENTICATED', J('ログインの画面へ', 'Go to the sign-in screen')),
        (J('共通: 要求の形が違う', 'Common: the request is malformed'), '400 INVALID_REQUEST', J('欄を直す', 'Fix the fields')),
    ]
    ifcs = [
        ifc('IFC-01', J('提出の API', 'Submission API'), 'http', 'ELM-03', ['ELM-01'], ['FR-01', 'FR-02', 'FR-06'],
            [('POST /api/v1/uploads', J('署名付き URL を返す', 'Returns a signed URL')),
             ('POST /api/v1/submissions', J('提出を確定し、受領を返す', 'Confirms the submission and returns the receipt')),
             ('GET /api/v1/submissions/{id}', J('提出と受領を返す', 'Returns the submission and its receipt')),
             ('PUT /api/v1/drafts/{id}', J('下書きを保存する', 'Saves the draft'))],
            [('POST /api/v1/submissions: ' + J('締め切りを過ぎた', 'the deadline has passed'), '409 DEADLINE_PASSED',
              J('締め切りを過ぎたと示す', 'Show that the deadline has passed')),
             ('POST /api/v1/submissions: ' + J('ファイルがストレージにない', 'the file is not in the storage'), '422 FILE_MISSING',
              J('もう一度ファイルを置く', 'Upload the file again'))] + common_errors, spec='ifc/specs/submissions.openapi.yaml'),
        ifc('IFC-02', J('採点の API', 'Grading API'), 'http', 'ELM-03', ['ELM-02'], ['FR-03', 'FR-05', 'FR-08'],
            [('GET /api/v1/teacher/submissions', J('担当の提出の一覧', "Lists the teacher's submissions")),
             ('PUT /api/v1/teacher/submissions/{id}/grade', J('採点を保存する', 'Saves the grade')),
             ('POST /api/v1/teacher/submissions/{id}/return', J('返却して通知する', 'Returns the submission and notifies')),
             ('GET /api/v1/teacher/reports/monthly', J('月次のレポートを返す', 'Returns the monthly report'))],
            [('POST /api/v1/teacher/submissions/{id}/return: ' + J('採点が済んでいない', 'not graded yet'), '409 NOT_GRADED',
              J('採点を促す', 'Ask for the grade first'))] + common_errors, spec='ifc/specs/teacher.openapi.yaml'),
        ifc('IFC-03', J('ストレージへのファイル', 'Files in the storage'), 'file', 'ELM-05', ['ELM-01', 'ELM-03'], ['FR-01'],
            [(J('署名付き URL への PUT', 'PUT to the signed URL'), J('ファイルを置く', 'Stores the file'))],
            [(J('URL の期限切れ', 'The URL has expired'), '403 (ObjectStore)', J('新しい URL をもらう', 'Get a new URL'))]),
        ifc('IFC-04', J('夜間の提出状況レポート', 'Nightly submission report'), 'batch', 'ELM-06', ['ELM-02'], ['FR-05'],
            [(J('nightly-report ジョブ', 'nightly-report job'), J('前の日までの提出を数えて書く', 'Counts the submissions up to the previous day'))],
            [(J('前の日の分が終わっていない', 'The previous day is not finished'), J('終わっていない日から続ける', 'Continues from the unfinished day'),
              J('なし', 'Nothing'))]),
    ]

    # ---------------- data
    def dat(i, entity, owner, store, consistency, retention, classification, relations=()):
        return item(i, entity, DAY3, S3, {'entity': entity, 'owner': owner, 'store': store, 'key_attributes': [],
                                          'relations': [{'to': t, 'kind': k, 'note': n} for t, k, n in relations],
                                          'consistency': consistency, 'retention': retention,
                                          'classification': classification, 'drivers': [], 'as_is': 'new'})
    dats = [
        dat('DAT-01', J('課題', 'Assignment'), 'ELM-03', 'ELM-04', J('講師の要求ごとに書く', 'Written per request from teachers'),
            J('学年の終わりまで', 'Until the end of the school year'), 'internal', [('DAT-02', 'one-to-many', J('提出', 'Submissions'))]),
        dat('DAT-02', J('提出', 'Submission'), 'ELM-03', 'ELM-04',
            J('提出の記録と受領を一つのトランザクションで書く（DEC-03）。受領の番号は記録の ID から作る',
              "The record and the receipt are written in one transaction (DEC-03). The receipt number comes from the record's ID"),
            J('卒業の後 1 年', 'One year after graduation'), 'personal', [('DAT-03', 'one-to-one', J('ファイル', 'File'))]),
        dat('DAT-03', J('提出のファイル', 'Submitted file'), 'ELM-01', 'ELM-05', J('署名付き URL で一度だけ置く', 'Uploaded once through a signed URL'),
            J('卒業の後 1 年', 'One year after graduation'), J('personal（生徒の答案）', "personal (students' answers)")),
        dat('DAT-04', J('採点', 'Grade'), 'ELM-03', 'ELM-04', J('講師の採点ごとに書く', 'Written per grading'),
            J('卒業の後 1 年', 'One year after graduation'), 'personal'),
    ]

    # ---------------- findings
    fnds = [
        {'id': 'FND-01', 'title': J('受領を記録より先に示している', 'The receipt is shown before the record is written'), 'status': 'accepted',
         'version': 1, 'basis': 'inferred', 'basis_note': None, 'needs_agreement': False, 'approver_candidates': [],
         'raised_by': 'design-review', 'raised_in': 'reviews/2026-09-20-architecture.md', 'to': 'architecture-drivers-to-architecture',
         'targets': ['DEC-03'], 'severity': 'major', 'evidence': J('受領の後に記録が欠けうる', 'A record can go missing after the receipt'),
         'suggestion': J('記録を書いてから受領を返す', 'Write the record, then return the receipt'),
         'resolution': J('DEC-03 を直した', 'DEC-03 changed'), 'changelog': [{'version': 1, 'date': '2026-09-20', 'change': J('作成', 'Raised'), 'reason': J('第 2 段階のレビュー', 'Review of stage 2')}]},
        {'id': 'FND-02', 'title': J('トレース ID の引き継ぎがない', 'No trace ID is passed on'), 'status': 'accepted',
         'version': 1, 'basis': 'inferred', 'basis_note': None, 'needs_agreement': False, 'approver_candidates': [],
         'raised_by': 'design-review', 'raised_in': 'reviews/2026-09-20-architecture.md', 'to': 'architecture-drivers-to-architecture',
         'targets': ['DEC-05'], 'severity': 'minor', 'evidence': J('ブラウザの失敗がつながらない', 'Browser failures are not linked'),
         'suggestion': J('ブラウザで ID を作る', 'Create the ID in the browser'), 'resolution': J('DEC-05 を直した', 'DEC-05 changed'),
         'changelog': [{'version': 1, 'date': '2026-09-20', 'change': J('作成', 'Raised'), 'reason': J('第 2 段階のレビュー', 'Review of stage 2')}]},
    ]

    # ---------------- reports
    def table(head, rows):
        out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
        out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
        return '\n'.join(out)

    def mmd(src):
        return '```mermaid\n' + src.strip('\n') + '\n```'

    BASIS = J({'stated': '入力', 'inferred': '推定', 'confirmed': '確認済み'}, {'stated': 'Stated', 'inferred': 'Inferred', 'confirmed': 'Confirmed'})
    KIND = J({'quality': '品質', 'change': '変更', 'constraint': '制約', 'function': '機能', 'observability': '観測', 'security': 'セキュリティ'},
             {'quality': 'Quality', 'change': 'Change', 'constraint': 'Constraint', 'function': 'Function', 'observability': 'Observability',
              'security': 'Security'})
    LEVEL = J({'high': '高', 'medium': '中', 'low': '低'}, {'high': 'High', 'medium': 'Medium', 'low': 'Low'})
    YES, NO = J('はい', 'Yes'), J('いいえ', 'No')
    sep = J('、', ', ')
    live = [d for d in drvs if d['status'] != 'retired']

    def did(d):
        return f'{d["id"]} {d["title"]}'

    r1 = [f'# {J("設計を動かす要求", "Architecture drivers")}: {SYS}', '',
          J(f'状態: 回答反映済み · 更新: {DAY1} · 第 1 段階（全 4 段階）', f'Status: answers applied · Updated: {DAY1} · Stage 1 of 4'), '',
          f'## {J("要約", "Summary")}', '',
          J('主な設計を動かす要求は四つ（締め切り前の集中、受領と記録の一致、外部のストレージ、確定の速さ）。費用と体制では実現できる見込み。',
            'Four primary drivers (the deadline rush, receipts matching records, the external storage, fast confirmation). Feasible with this budget and team.'), '',
          f'## {J("設計の前提と利害関係者", "Design inputs and stakeholders")}', '',
          table(['ID', J('種類', 'Kind'), J('内容', 'Statement'), J('出どころ', 'Source'), J('根拠', 'Basis')],
                [[x['id'], J('技術制約: ', 'Technology constraint: ') + {'mandated': J('使う', 'Mandated'), 'external-service': J('外部サービス', 'External service'),
                                                                        'platform': J('基盤', 'Platform')}[x['kind']], x['statement'], x['source'], BASIS[x['basis']]]
                 for x in ctx['technology_constraints']]
                + [[x['id'], {'budget': J('予算', 'Budget'), 'deadline': J('納期', 'Deadline'), 'team': J('体制', 'Team')}[x['kind']],
                    x['statement'], x['source'], BASIS[x['basis']]] for x in ctx['project_constraints']]
                + [['TEAM-01', J('チーム', 'Team'), ctx['teams'][0]['name'], '—', BASIS['stated']],
                   ['CHG-01', J('将来の変更', 'Anticipated change'), ctx['anticipated_changes'][0]['change'], ctx['anticipated_changes'][0]['source'], BASIS['stated']],
                   ['STK-01', J('利害関係者', 'Stakeholder'), ctx['stakeholders'][0]['role'], ctx['stakeholders'][0]['source'], BASIS['inferred']]]), '',
          f'## {J("関心事の一覧", "Concern inventory")}', '',
          table([J('入力の項目', 'Input item'), J('種類', 'Kind'), J('誰の関心事', 'Whose concern'), J('なったもの', 'Became')],
                [['QR-01', J('品質', 'Quality'), 'USR-01', 'DRV-01'], ['QR-02', J('品質', 'Quality'), 'USR-01', 'DRV-02'],
                 ['QR-03, QR-07', J('品質', 'Quality'), 'USR-01, USR-04', 'DRV-03'], ['QR-09', J('品質', 'Quality'), 'USR-01', 'DRV-08'],
                 ['QR-10', J('品質', 'Quality'), 'USR-03', 'DRV-07'], ['TC-02', J('制約', 'Constraint'), 'STK-01', 'DRV-05'],
                 ['PC-01, PC-03', J('制約', 'Constraint'), 'STK-01', 'DRV-06'], ['CHG-01', J('変更', 'Change'), 'STK-01', 'DRV-04'],
                 ['QR-04', J('品質', 'Quality'), 'USR-02', J('置いた: 今期は対象外', 'set aside: excluded this cycle')]]), '',
          f'## {J("設計を動かす要求", "Architecture drivers")}', '',
          f'### {J("品質と変更のシナリオ", "Quality and change scenarios")}', '',
          table(['DRV', J('出どころ', 'Source'), J('刺激', 'Stimulus'), J('対象', 'Artifact'), J('環境', 'Environment'), J('応答', 'Response'),
                 J('応答の測定量', 'Measure'), J('根拠', 'Basis')],
                [[did(d)] + [d['scenario'][k] for k in ('source', 'stimulus', 'artifact', 'environment', 'response', 'measure')] + [BASIS['inferred']]
                 for d in live if d['kind'] in ('quality', 'change')]), '',
          f'### {J("制約", "Constraints")}', '',
          table(['DRV', J('制約', 'Constraint'), J('交渉', 'Negotiable'), J('出どころ', 'Source'), J('根拠', 'Basis')],
                [[did(d), d['statement'], J('交渉できない', 'Non-negotiable'), sep.join(d['sources']), BASIS['stated']]
                 for d in live if d['kind'] == 'constraint']
                + [[J('DRV-10（廃止）', 'DRV-10 (retired)'), J('DRV-05 に統合した', 'Merged into DRV-05'), '—', '—', '—']]), '',
          f'### {J("機能・観測・セキュリティの要求", "Functional, observability and security drivers")}', '',
          table(['DRV', J('種類', 'Kind'), J('内容', 'Statement'), J('出どころ', 'Sources'), J('根拠', 'Basis')],
                [[did(d), KIND[d['kind']], d['statement'], sep.join(d['sources']), BASIS['inferred']]
                 for d in live if d['kind'] in ('function', 'observability', 'security')]), '',
          f'### {J("全体の原則", "Principles")}', '',
          table(['DRV', J('原則', 'Principle'), J('導いたもと', 'Derived from'), J('根拠', 'Basis')],
                [[did(d), d['statement'], sep.join(d['derived_from']), BASIS['inferred']] for d in live if d['kind'] == 'principle']), '',
          f'## {J("順位表", "Ranking table")}', '',
          table([J('順位', 'Rank'), 'DRV', J('事業の優先度', 'Business priority'), J('理由', 'Reason'), J('設計上の難しさ', 'Design difficulty'),
                 J('理由', 'Reason'), J('主', 'Primary')],
                [[d['priority']['rank'], d['id'], LEVEL[d['priority']['business']], d['priority']['business_reason'],
                  LEVEL[d['priority']['difficulty']], d['priority']['difficulty_reason'], YES if d['primary'] else NO]
                 for d in sorted((d for d in live if d['priority']), key=lambda d: d['priority']['rank'])]), '',
          J('主な要求は順位 4 まで。', 'The first four are primary.'), '',
          f'## {J("競合", "Conflicts")}', '',
          table([J('要求', 'Drivers'), J('競合', 'Conflict'), J('解き方', 'Resolved by')],
                [[J('DRV-01 と DRV-02', 'DRV-01 and DRV-02'), J('受領の前に記録を書くと、確定が遅くなる', 'Writing the record before the receipt slows the confirmation'),
                  J('第 2 段階', 'Stage 2')]]), '',
          f'## {J("実現できるか", "Feasibility")}', '',
          table([J('主な要求', 'Primary driver'), J('判定', 'Verdict')],
                [['DRV-01', J('できる: ファイルをサーバーに通さなければ、一つのサーバーで受けられる', 'Yes: one server is enough if files do not pass through it')],
                 ['DRV-03', J('できる: 一つのトランザクションで書く', 'Yes: written in one transaction')],
                 ['DRV-05', J('できる: ObjectStore の署名付き URL を使う', "Yes: with ObjectStore's signed URLs")],
                 ['DRV-02', J('できる見込み: 確定の区間の予算で確かめる', 'Likely: checked with the hop budgets of confirmation')]]), '',
          f'## {J("質問と回答", "Questions and answers")}', '',
          table(['#', J('質問', 'Question'), J('下書きの答え', 'Drafted answer'), J('回答', 'Answer'), J('変わったこと', 'What changed')],
                [['1', J('締め切り前の最大の件数は？', 'The peak number of submissions before a deadline?'), J('1 分に 300 件', '300 a minute'),
                  J('そのとおり', 'As drafted'), J('なし', 'Nothing')]]), '']

    walk = {
        'CUJ-01': [[J('課題を開く', 'Open the assignment'), 'FR-01', 'ELM-01, ELM-03', J('ELM-01 → ELM-03 課題の取得', 'ELM-01 → ELM-03 gets the assignment'), J('なし', 'none')],
                   [J('ファイルを添付する', 'Attach a file'), 'FR-01', 'ELM-01, ELM-05', J('ELM-01 → ELM-05 署名付き URL で置く', 'ELM-01 → ELM-05 upload with a signed URL'), J('なし', 'none')],
                   [J('提出する', 'Submit'), 'FR-01, FR-02', 'ELM-01, ELM-03, ELM-04', J('ELM-03 が記録を書いて受領を返す', 'ELM-03 writes the record and returns the receipt'), J('なし', 'none')]],
        'CUJ-02': [[J('提出を開く', 'Open the submission'), 'FR-03', 'ELM-02, ELM-03, ELM-05', J('ELM-02 → ELM-03 一覧と内容', 'ELM-02 → ELM-03 list and contents'), J('なし', 'none')],
                   [J('採点する', 'Grade'), 'FR-03', 'ELM-02, ELM-03', J('採点を保存する', 'Saves the grade'), J('なし', 'none')],
                   [J('返却する', 'Return'), 'FR-03, FR-08', 'ELM-02, ELM-03', J('返却して通知する', 'Returns and notifies'), J('なし', 'none')]],
        'CUJ-04': [[J('レポートを開く', 'Open the report'), 'FR-05', 'ELM-02, ELM-03, ELM-06', J('前の日までのレポート', 'The report up to the previous day'), J('なし', 'none')]],
    }
    cuj_names = {'CUJ-01': J('課題の提出', 'Submit homework'), 'CUJ-02': J('採点と返却', 'Grade and return'),
                 'CUJ-03': J('提出の失敗の調査', 'Investigate a failed submission'), 'CUJ-04': J('月次の提出状況の確認', 'Check monthly submissions')}
    WH = [J('手順', 'Step'), 'FR', J('要素', 'Elements'), J('やり取り', 'Interactions'), J('欠け', 'Gap')]
    walk_md = []
    for cuj in ('CUJ-01', 'CUJ-02', 'CUJ-03', 'CUJ-04'):
        walk_md += [f'**{cuj} {cuj_names[cuj]}**', '']
        if cuj == 'CUJ-03':
            walk_md += [J('知らせを受けた開発者が、トレース ID でログをたどり、原因を直す（DEC-05）。手順ごとの表にするほどの手順はない。',
                          'The developer who gets the notice traces the logs with the trace ID and fixes the cause (DEC-05). Too few steps for a table.'), '']
        else:
            walk_md += [table(WH, walk[cuj]), '']

    dec_rows = [[d['id'], d['question'], d['chosen'] or '—', sep.join(d['addresses']),
                 J('。', '. ').join(f'{r["option"]}（{r["reason"]}）' if lang == 'ja' else f'{r["option"]} ({r["reason"]})' for r in d['rejected']) or '—',
                 BASIS['inferred']] for d in decs if d['stage'] == 'architecture' and d['id'] != 'DEC-06']   # DEC-06 left out on purpose
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
  sa -->|"F1 提出、F2 下書き"| api
  ta -->|"F3 採点と返却"| api
  sa -->|"F4 ファイル"| os
  api -->|"F5 読み書き"| db''', '''flowchart LR
  subgraph tdev["Trust boundary: student and teacher devices"]
    sa["ELM-01 Student web app"]
    ta["ELM-02 Teacher web app"]
  end
  subgraph tsys["Trust boundary: the school's cloud"]
    api["ELM-03 API server"]
    db[("ELM-04 Database")]
  end
  os[["ELM-05 External storage"]]
  sa -->|"F1 submission, F2 draft"| api
  ta -->|"F3 grading and returns"| api
  sa -->|"F4 file"| os
  api -->|"F5 reads and writes"| db''')
    threat_rows = J([
        ['F1 ELM-01 → ELM-03 提出', '端末 → 塾のクラウド', '他人になりすまして提出する: セッション（DEC-01）', '期限を書き換える: サーバーが判定する'],
        ['F2 ELM-01 → ELM-03 下書き', '端末 → 塾のクラウド', '他人の下書きを読む: 本人だけ（DRV-08）', '—'],
        ['F3 ELM-02 → ELM-03 採点と返却', '端末 → 塾のクラウド', '担当でない講師が採点する: 担当を確かめる（FND-02）', '点数を書き換える: 記録を残す'],
        ['F4 ELM-01 → ELM-05 ファイル', '端末 → 外部サービス', 'URL を盗んで置く: 15 分の期限（DEC-02 版 2）', '—'],
        ['F5 ELM-03 → ELM-04 読み書き', '塾のクラウドの中', '—', '—']], [
        ['F1 ELM-01 → ELM-03 submission', 'device → school cloud', 'Submitting as someone else: session (DEC-01)', 'Changing the deadline: the server decides'],
        ['F2 ELM-01 → ELM-03 draft', 'device → school cloud', "Reading someone else's draft: owner only (DRV-08)", '—'],
        ['F3 ELM-02 → ELM-03 grading and returns', 'device → school cloud', 'A teacher who does not teach the class grades: the class is checked (FND-02)', 'Changing a grade: it is recorded'],
        ['F4 ELM-01 → ELM-05 file', 'device → external service', 'Uploading with a stolen URL: 15-minute expiry (DEC-02 version 2)', '—'],
        ['F5 ELM-03 → ELM-04 reads and writes', 'inside the school cloud', '—', '—']])
    r2 = [f'# {J("アーキテクチャ", "Architecture")}: {SYS}', '',
          J(f'状態: 回答反映済み · 更新: {DAY2} · 第 2 段階（全 4 段階）', f'Status: answers applied · Updated: {DAY2} · Stage 2 of 4'), '',
          f'## {J("要約", "Summary")}', '', J('一つの API サーバーと二つの Web アプリ。ファイルはストレージに直接置く。', 'One API server and two web apps; files go straight to the storage.'), '',
          f'## {J("全体の構造", "Overall structure")}', '',
          J('一つの API サーバー（ELM-03）が、二つの Web アプリ（ELM-01、02）からの要求を受ける。提出のファイルは署名付き URL で外部のストレージ（ELM-05）に直接置く（DEC-02）。',
            'One API server (ELM-03) takes requests from the two web apps (ELM-01, 02). Submitted files go straight to the external storage (ELM-05) through signed URLs (DEC-02).'), '',
          table([J('要求（順位）', 'Driver (rank)'), O1[0], O2[0], O3[0]],
                [[J('DRV-01（1）', 'DRV-01 (1)'), J('満たす', 'Meets'), J('満たす', 'Meets'), J('満たす', 'Meets')],
                 [J('DRV-06（5）', 'DRV-06 (5)'), J('満たす', 'Meets'), J('満たさない', 'Fails'), J('一部', 'Partly')]]), '',
          f'## {J("設計の決定", "Decisions")}', '',
          table(['DEC', J('問い', 'Question'), J('選んだ案', 'Chosen'), J('対象', 'Addresses'), J('退けた案', 'Rejected'), J('根拠', 'Basis')], dec_rows), '',
          f'### DEC-02 {J("ファイルの置き方", "How files are stored")}', '',
          table([J('要求（順位）', 'Driver (rank)'), U1[0], U2[0]], [[J('DRV-01（1）', 'DRV-01 (1)'), J('満たす', 'Meets'), J('満たさない', 'Fails')]]), '',
          f'- {J("得るもの: 締め切り前もサーバーが詰まらない。", "Gains: the server does not choke before deadlines.")}', '',
          f'## {J("設計の観点", "Design concerns")}', '',
          table([J('観点', 'Concern'), J('決めた決定、または標準のやり方で足りる理由', 'Settled by, or why standard practice is enough')],
                [[J('並行性', 'Concurrency'), J('同じ提出の送り直しは冪等キーで一つにする（DEC-08）', 'Retried submissions are made one by idempotency keys (DEC-08)')],
                 [J('データの永続化', 'Data persistence'), J('記録と受領を一つのトランザクションで書く（DEC-03）。前の版は受領を先に示していた。', 'The record and the receipt are written in one transaction (DEC-03). The previous version showed the receipt first.')],
                 [J('エラー処理と障害許容', 'Error handling and fault tolerance'), J('ストレージの障害では提出を止め、もう一度試すよう示す', 'On a storage outage, submissions stop and ask to try again')],
                 [J('可変性', 'Variability'), J('標準のやり方で足りる', 'Standard practice is enough')]]), '',
          f'## {J("脅威のモデル", "Threat model")}', '',
          J('守るもの: 生徒の答案、提出の記録、採点。', "Assets: students' answers, submission records, grades."), '',
          mmd(threat), '',
          table(J(['流れ', '越える境界', 'なりすまし', '書き換え'], ['Flow', 'Crosses', 'Spoofing', 'Tampering']), threat_rows), '',
          f'## {J("要素", "Elements")}', '',
          table(['ELM', J('種類', 'Kind'), J('名前', 'Name'), J('責務', 'Responsibility'), 'FR', J('要求', 'Drivers'), J('チーム', 'Team'), J('差分', 'As-is'), J('根拠', 'Basis')],
                [[e['id'], {'component': J('コンポーネント', 'Component'), 'data-store': J('データの置き場所', 'Data store'),
                            'external-system': J('外部システム', 'External system'), 'node': J('実行環境', 'Node')}[e['kind']],
                  e['name'], e['responsibility'], sep.join(e['functions']) or '—', sep.join(e['drivers']) or '—', e['team'] or '—',
                  J('新設', 'New'), BASIS['inferred']] for e in elms]), '',
          f'## {J("ビュー", "Views")}', '',
          f'### {J("外部との関係", "Context")}', '', mmd(flows_ctx), '',
          f'### {J("実行時の構成", "Runtime")}', '',
          mmd(J('flowchart LR\n  sa["ELM-01"] -->|"提出"| api["ELM-03"]\n  api -->|"記録"| db[("ELM-04")]\n  sa -->|"ファイル"| os[["ELM-05"]]',
                'flowchart LR\n  sa["ELM-01"] -->|"submission"| api["ELM-03"]\n  api -->|"record"| db[("ELM-04")]\n  sa -->|"file"| os[["ELM-05"]]')), '',
          table([J('待つもの', 'Waits'), J('待たれるもの', 'Waited on'), J('待つ上限', 'Limit')],
                [['ELM-01', 'ELM-03', J('10 秒', '10 s')], ['ELM-03', 'ELM-04', J('2 秒', '2 s')]]), '',
          f'### {J("配置", "Deployment")}', '',
          mmd(J('flowchart TB\n  subgraph n["ELM-07 クラウドの実行環境"]\n    api["ELM-03"]\n    bat["ELM-06"]\n  end\n  api --> db[("ELM-04")]\n  bat --> db',
                'flowchart TB\n  subgraph n["ELM-07 Cloud runtime"]\n    api["ELM-03"]\n    bat["ELM-06"]\n  end\n  api --> db[("ELM-04")]\n  bat --> db')), '',
          table([J('実行環境', 'Node'), J('動くもの', 'Runs'), J('数', 'Count'), J('いつ', 'When'), J('一緒に止まるもの', 'Fails with')],
                [['ELM-07', 'ELM-03, ELM-06', '1', J('いつも', 'Always'), J('提出と採点', 'Submissions and grading')]]), '',
          f'### {J("情報", "Information")}', '',
          mmd(J('flowchart LR\n  a["DAT-01 課題"] --> s["DAT-02 提出"]\n  s --> f["DAT-03 提出のファイル"]\n  s --> g["DAT-04 採点"]',
                'flowchart LR\n  a["DAT-01 Assignment"] --> s["DAT-02 Submission"]\n  s --> f["DAT-03 Submitted file"]\n  s --> g["DAT-04 Grade"]')), '',
          f'### {J("コードの分け方", "Code structure")}', '',
          mmd('flowchart TB\n  web["web"] --> contracts["contracts"]\n  server["server"] --> application["application"]\n  application --> domain["domain"]'), '',
          J('依存の規則（CI で確かめる）:', 'Dependency rules (checked in CI):'), '',
          J('- `domain` は何にも依存しない。', '- `domain` depends on nothing.'), '',
          f'## {J("通し確認", "Walkthroughs")}', '',
          f'### {J("CUJ", "CUJs")}', ''] + walk_md + [
          f'### {J("主な設計を動かす要求", "Primary drivers")}', '',
          table(['DRV', J('刺激が入る所', 'Where the stimulus enters'), J('応答を形づくる決定', 'Decisions that shape the response'),
                 J('測定量を満たすか', 'Meets the measure?'), J('残る危険', 'Remaining risk')],
                [['DRV-01', 'ELM-03', 'DEC-01, DEC-02', J('満たす見込み', 'Likely'), J('ストレージの障害', 'A storage outage')],
                 ['DRV-03', 'ELM-03', 'DEC-03', J('満たす', 'Yes'), J('なし', 'None')],
                 ['DRV-05', 'ELM-01', 'DEC-02', J('満たす', 'Yes'), J('なし', 'None')],
                 ['DRV-02', 'ELM-03', 'DEC-03', J('満たす見込み（第 3 段階の予算）', 'Likely (stage 3 budget)'), J('書き込みの遅れ', 'A slow write')]]), '',
          f'## {J("設計上の値", "Design parameters")}', '',
          table([J('値', 'Parameter'), J('仮の値', 'Value'), J('もと', 'Basis'), J('決定', 'Decision')],
                [[p['name'], p['value'], p['basis'], d['id']] for d in decs if d['stage'] == 'architecture' for p in d['parameters']]), '',
          f'## {J("技術的負債と先送りした決定", "Debt and deferred decisions")}', '',
          table(['DEC', J('負債か先送りか', 'Debt or deferral'), J('理由', 'Why'), J('返す・見直すとき', 'Repay or revisit when')],
                [['DEC-04', J('負債: ', 'Debt: ') + decs[3]['debt']['what'], decs[3]['debt']['why_accepted'], decs[3]['debt']['repay_when']],
                 ['DEC-06', J('先送り: ', 'Deferred: ') + decs[5]['question'], decs[5]['rationale'], decs[5]['revisit_when']]]), '',
          f'## {J("費用と体制", "Cost and team")}', '',
          f'### {J("走る費用", "Running cost")}', '',
          table([J('費用のもと', 'Cost driver'), J('使う量', 'Usage'), J('値段と無料の枠', 'Price and free tier'), J('上限の仕組み', 'Cap')],
                [[J('実行環境', 'Runtime'), J('一つ、いつも', 'One, always'), J('月 1 万円', '10,000 yen a month'), J('予算の知らせ', 'Budget alert')],
                 [J('ストレージ', 'Storage'), J('年 50 GB', '50 GB a year'), J('月 2 千円', '2,000 yen a month'), J('なし', 'None')]]), '',
          f'## {J("質問と回答", "Questions and answers")}', '',
          table(['#', J('質問', 'Question'), J('下書きの答え', 'Drafted answer'), J('回答', 'Answer'), J('変わったこと', 'What changed')],
                [['4', J('トレース ID はどこで作るか', 'Where is the trace ID created?'), J('ブラウザ', 'The browser'), J('そのとおり', 'As drafted'), 'DEC-05']]), '']

    hop = J([['ELM-01 が要求を送る', '0.30 秒', '仮'], ['ELM-03 の処理', '0.20 秒', '仮'],
             ['ELM-04 に記録と受領を書く（DEC-03）', '0.50 秒', '仮。書き込みの 99 パーセンタイル'],
             ['ブラウザに戻って示す', '0.50 秒', '仮'], ['余り', '1.50 秒', ''], ['合計', '3.00 秒', 'NFR-06 のしきい値']],
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
    r3 = [f'# {J("概要設計", "High-level design")}: {SYS}', '',
          J(f'状態: 回答反映済み · 更新: {DAY3} · 第 3 段階（全 4 段階）', f'Status: answers applied · Updated: {DAY3} · Stage 3 of 4'), '',
          f'## {J("要約", "Summary")}', '', J('インタフェースは四つ。確定の予算は 3 秒に収まる。', 'Four interfaces; the confirmation budget fits in 3 seconds.'), '',
          f'## {J("共通の約束事", "Shared conventions")}', '',
          table([J('約束事', 'Convention'), J('決めたこと', 'Decided'), 'DEC'],
                [[J('エラー', 'Errors'), J('問題の詳細に code と traceId', 'Problem details with a code and a traceId'), 'DEC-07'],
                 [J('冪等キーと送り直し', 'Idempotency keys and retries'), J('状態を変える要求すべてに Idempotency-Key', 'An Idempotency-Key on every state-changing request'), 'DEC-08']]), '',
          f'## {J("設計の決定", "Decisions")}', '',
          table(['DEC', J('問い', 'Question'), J('選んだ案', 'Chosen'), J('退けた案', 'Rejected'), J('根拠', 'Basis')],
                [[d['id'], d['question'], d['chosen'], sep.join(r['option'] for r in d['rejected']), BASIS['inferred']]
                 for d in decs if d['stage'] == 'high-level-design']), '',
          f'## {J("インタフェース", "Interfaces")}', '',
          table(['IFC', J('種類', 'Kind'), J('名前', 'Name'), J('提供側', 'Provider'), J('利用側', 'Consumers'), J('操作', 'Operations'), 'FR', J('仕様', 'Spec'), J('根拠', 'Basis')],
                [[i['id'], {'http': 'HTTP', 'file': J('ファイル', 'File'), 'batch': J('バッチ', 'Batch')}[i['kind']], i['name'], i['provider'],
                  sep.join(i['consumers']), str(len(i['operations'])), sep.join(i['functions']), (i['spec'] or '—').split('/')[-1], BASIS['inferred']]
                 for i in ifcs]), '',
          f'## {J("エラーの決まり", "Error contracts")}', '',
          table(['IFC', J('操作', 'Operation'), J('場合', 'Case'), J('知らせ方', 'Signal'), J('呼ぶ側', 'The caller')],
                [[i['id'], (e['case'].split(': ', 1)[0] if ': ' in e['case'] else '—'), e['case'].split(': ', 1)[-1], e['signal'], e['caller_does']]
                 for i in ifcs for e in i['errors']]), '',
          f'## {J("端から端の流れ", "End-to-end flows")}', '',
          f'### CUJ-01 {cuj_names["CUJ-01"]}', '', mmd(seq1), '',
          f'### CUJ-02 {cuj_names["CUJ-02"]}', '', mmd(seq2), '',
          f'### DRV-01 {J("受け付け続ける", "Keep accepting")}', '', mmd(seq3), '',
          f'## {J("遅延の予算", "Latency budgets")}', '',
          J('予算はタイムアウトではない。', 'The budgets are not timeouts.'), '',
          f'### NFR-06{J("（提出の確定の 95 パーセンタイルが 3 秒以内）", " (the 95th percentile of submission confirmation within 3 seconds)")}', '',
          J('測る区間は、ブラウザが送ってから受領を示すまで。', 'Measured from the browser sending the request to the receipt being shown.'), '',
          table([J('区間', 'Hop'), J('予算（99 パーセンタイル。4 区間）', 'Budget (99th percentile, 4 hops)'), J('もと', 'Basis')], hop), '',
          f'### NFR-02{J("（夜間レポートが 6:00 までに終わる）", " (the nightly report finishes by 6:00)")}', '',
          J('02:00 に起動し、4 時間の余裕がある（DEC-04）。区間の表にするほどの区間はない。',
            'It starts at 02:00, with four hours to spare (DEC-04). Too few hops for a table.'), '',
          f'### {J("失敗したときの流れとエラーバジェット", "Failure paths and error budgets")}', '',
          table(['SLO', J('28 日の有効な出来事', 'Valid events in 28 days'), J('許容される失敗の件数', 'Error budget volume'),
                 J('失敗したときの流れの扱い', 'How failure paths count')],
                [[J('NFR-01（SLI-01）', 'NFR-01 (SLI-01)'), J('提出 4 万件', '40,000 submissions'), J('200 件', '200'),
                  J('ストレージの障害の間の失敗はバジェットに入る', 'Failures during a storage outage count against the budget')]]), '',
          f'## {J("画面", "Screens")}', '',
          f'### CUJ-01 {cuj_names["CUJ-01"]}', '', mmd(screens1), '',
          f'### CUJ-02 {cuj_names["CUJ-02"]}', '', mmd(screens2), '',
          f'## {J("データ", "Data")}', '', mmd(er), '',
          table(['DAT', J('実体', 'Entity'), J('持ち主', 'Owner'), J('置き場所', 'Store'), J('整合の取り方', 'Consistency'),
                 J('保持期間', 'Retention'), J('扱いの区分', 'Classification'), J('根拠', 'Basis')],
                [[d['id'], d['entity'], d['owner'], d['store'], d['consistency'], d['retention'] or '—', d['classification'], BASIS['inferred']] for d in dats]), '',
          f'### {J("データの品質の流れ", "Data quality flows")}', '',
          J('月次のレポートの数（QR-08）:', 'The numbers of the monthly report (QR-08):'), '',
          mmd(dq), '',
          table([J('要求', 'Requirement'), J('どこから来るか', 'Comes from'), J('どう確かめるか', 'Checked by'), J('どう伝わるか', 'Passed on by'),
                 J('何と何を照らすか', 'Compared with')],
                [['QR-07', 'ELM-03', J('毎晩、受領と記録を照らす', 'Receipts against records every night'), 'ELM-06', J('受領と記録', 'Receipts and records')]]), '',
          f'## {J("要素をまたぐ状態", "States across elements")}', '',
          f'### {J("提出", "Submission")}{J("（ELM-01、ELM-03）", " (ELM-01, ELM-03)")}', '', mmd(states), '',
          J('submitted になるのは記録を書いた後だけ（DRV-09）。', 'It becomes submitted only after the record is written (DRV-09).'), '',
          f'## {J("測定点", "Measurement points")}', '',
          table(['SLI', J('出どころ', 'Produced by'), J('欄', 'Fields')],
                [['SLI-01', J('ELM-03 の要求のログ', "ELM-03's request log"), 'route, status, trace_id'],
                 ['SLI-02', J('ELM-06 の終わりの記録', "ELM-06's completion record"), 'finished_at']]), '',
          f'## {J("受け入れ基準のトレース", "Acceptance criteria trace")}', '',
          table(['FR', J('基準', 'Criterion'), 'IFC', J('流れ', 'Flow')],
                [['FR-01', J('提出を確定すると受領が出る', 'Confirming a submission shows a receipt'), 'IFC-01', 'CUJ-01'],
                 ['FR-01', J('締め切りの後は提出できない', 'No submission after the deadline'), 'IFC-01', 'CUJ-01'],
                 ['FR-03', J('採点して返却できる', 'A submission can be graded and returned'), 'IFC-02', 'CUJ-02']]), '',
          f'## {J("設計上の値", "Design parameters")}', '',
          table([J('値', 'Parameter'), J('仮の値', 'Value'), J('もと', 'Basis'), J('項目', 'Item')],
                [[p['name'], p['value'], p['basis'], d['id']] for d in decs if d['stage'] == 'high-level-design' for p in d['parameters']]), '']

    files = {'design-context.yaml': ctx}
    for d in drvs:
        files[f'drv/{d["id"]}.yaml'] = d
    for d in decs:
        files[f'dec/{d["id"]}.yaml'] = d
    for d in elms:
        files[f'elm/{d["id"]}.yaml'] = d
    for d in ifcs:
        files[f'ifc/{d["id"]}.yaml'] = d
    for d in dats:
        files[f'dat/{d["id"]}.yaml'] = d
    for d in fnds:
        files[f'fnd/{d["id"]}.yaml'] = d
    files['1-architecture-drivers.md'] = '\n'.join(r1)
    files['2-architecture.md'] = '\n'.join(r2)
    files['3-high-level-design.md'] = '\n'.join(r3)
    return files


STAGE3 = ('3-high-level-design.md', 'ifc/', 'dat/', 'dec/DEC-07.yaml', 'dec/DEC-08.yaml')


def write(case, lang, quality_case, stage3=True):
    base = EVALS / case / 'files' / 'docs'
    if base.exists():
        shutil.rmtree(base)
    d = base / 'design'
    for path, content in sorted(data(lang).items()):
        if not stage3 and path.startswith(STAGE3):
            continue
        p = d / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            p.write_text(content, encoding='utf-8')
        else:
            p.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False, width=1000), encoding='utf-8')
    src = QUALITY / quality_case / 'files' / 'docs' / 'quality'
    shutil.copytree(src, base / 'quality', ignore=shutil.ignore_patterns('summary.html'))
    print(f'書いた: {base.relative_to(ROOT)}')


if __name__ == '__main__':
    write('homework-service-full', 'ja', 'homework-service-full')
    write('homework-service-full-en', 'en', 'homework-service-full-en')
    write('homework-service-stage2', 'ja', 'homework-service-full', stage3=False)

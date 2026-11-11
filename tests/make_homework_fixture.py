#!/usr/bin/env python3
"""Build the outputs (docs/quality) of a fictional homework submission service (課題提出サービス),
to test shapes that the ride-hailing app does not have. The layout is that of cuj-to-slo 0.3.0.

  uv run --with pyyaml python3 tests/make_homework_fixture.py

Writes to these directories under skills/quality-summary-html/evals/:
  homework-service-full/files/docs/quality     stages 1 to 4, in Japanese
  homework-service-stage2/files/docs/quality   stages 1 and 2 only (no function proposals yet), in Japanese
  homework-service-full-en/files/docs/quality  stages 1 to 4, in English (the same items, to test the English page)
How it differs from the ride-hailing app: few items, a CUJ with two users, two EBPs, a deadline SLO, and one
FR missing from the report's coverage table (the script should report it as an inconsistency).
Shapes that cuj-to-slo 0.3.0 brought, each at least once: shared facts with IDs in context.yaml (CON, EXT with
creates_data, DIN, OPF), items that cite them in premises, assumptions (QAS) of every status, basis: assumed,
an FR that acts across CUJs (cuj and cuj_step null), a QIU covered in more than one way (one coverage row each),
a confirmed SLO target, SLIs with a vantage instead of a method, and report headers with "Inputs as of".
The reports hold only the tables the script reads, written as the 0.3.0 templates write them.
"""
import pathlib
import shutil

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'skills' / 'quality-summary-html' / 'evals'
# (updated, inputs as of) for each stage's report
HEAD = {1: ('2026-09-01', None), 2: ('2026-09-03', '3f1c2ab'), 3: ('2026-09-08', '7d0e4b9'), 4: ('2026-09-12', 'b52e8c1')}


def data(lang):
    """Every item and report of the fictional project, in Japanese (ja) or English (en)"""
    def J(ja, en):
        return ja if lang == 'ja' else en

    def common(i, title, basis='inferred', note=None, premises=()):
        return {'id': i, 'title': title, 'status': 'active', 'basis': basis, 'basis_note': note, 'premises': list(premises)}

    SRC = J('入力の要望書', 'The request document in the inputs')
    D = {}
    D['context'] = {
        'system': {
            'name': J('課題提出サービス（homework-portal）', 'Homework submission service (homework-portal)'),
            'boundary': J('生徒と講師が課題を配り、提出し、採点して返す仕組みと、塾の事務が見る月次のレポート。保護者向けの画面と月謝の決済は除く。',
                          'Where students and teachers hand out, submit, grade and return homework, and the monthly report the cram school '
                          "office reads. The parents' screens and tuition payments are left out."),
            'purpose': J('生徒が期限までに課題を出し、講師が早く返せるようにする', 'Students hand in homework by the deadline, and teachers return it quickly'),
            'basis': 'stated',
        },
        'constraints': [{'id': 'CON-01', 'statement': J('提出の期限は、講師が課題ごとに決める', 'Teachers set the deadline of each assignment'),
                         'source': SRC, 'basis': 'stated'}],
        'external_systems': [{'id': 'EXT-01', 'role': J('外部のストレージ（提出したファイルを保管する）', 'External storage (keeps the submitted files)'),
                              'creates_data': True, 'source': SRC, 'basis': 'stated'}],
        'design_inputs': [{'id': 'DIN-01', 'statement': J('生徒と講師の画面は、ブラウザで動く Web アプリにする',
                                                          'The student and teacher screens are a web app that runs in the browser'),
                           'source': SRC, 'basis': 'stated'}],
        'kgis': [{'id': 'KGI-01', 'name': J('継続率', 'Retention'),
                  'measure': J('月末に在籍している生徒 ÷ 月初に在籍していた生徒', 'Students enrolled at month end ÷ students enrolled at month start'),
                  'target': '95%', 'basis': 'stated'}],
        'outcomes': [
            {'id': 'OUT-01', 'statement': J('期限までに課題を提出する生徒を増やす', 'Increase the students who submit homework by the deadline'),
             'verb': 'increase', 'kgis': ['KGI-01'], 'basis': 'stated'},
            {'id': 'OUT-02', 'statement': J('返却の遅れについての問い合わせを減らす', 'Decrease the inquiries about late returns'),
             'verb': 'decrease', 'kgis': ['KGI-01'], 'basis': 'inferred'},
        ],
        'users': [
            {'id': 'USR-01', 'name': J('生徒', 'Student'), 'category': 'primary', 'data_role': 'both', 'considered': True, 'exclusion_reason': None, 'basis': 'stated'},
            {'id': 'USR-02', 'name': J('講師', 'Teacher'), 'category': 'primary', 'data_role': 'both', 'considered': True, 'exclusion_reason': None, 'basis': 'stated'},
            {'id': 'USR-03', 'name': J('開発者', 'Developer'), 'category': 'secondary-maintenance', 'data_role': 'consumer', 'considered': True,
             'exclusion_reason': None, 'basis': 'inferred', 'basis_note': J('障害の調査をする人として推定', 'Inferred as the person who investigates failures')},
            {'id': 'USR-04', 'name': J('塾の事務', 'Cram school office'), 'category': 'indirect', 'data_role': 'consumer', 'considered': True,
             'exclusion_reason': None, 'basis': 'stated'},
            {'id': 'USR-05', 'name': J('保護者', 'Parent'), 'category': 'indirect', 'data_role': 'consumer', 'considered': False,
             'exclusion_reason': J('今期は保護者向けの画面を作らない（質問 2）', 'No screens for parents this cycle (question 2)'), 'basis': 'confirmed'},
        ],
        'cujs': [
            {'id': 'CUJ-01', 'name': J('課題の提出', 'Submit homework'), 'users': ['USR-01'],
             'user_goal': J('期限までに、正しいファイルを迷わず提出する', 'Submit the right file by the deadline without getting lost'),
             'steps': [J('課題を開く', 'Open the assignment'), J('ファイルを添付する', 'Attach a file'), J('提出する', 'Submit')],
             'outcomes': ['OUT-01'], 'basis': 'stated'},
            {'id': 'CUJ-02', 'name': J('採点と返却', 'Grade and return'), 'users': ['USR-02'],
             'user_goal': J('提出を早く採点し、講評を付けて返す', 'Grade submissions quickly and return them with comments'),
             'steps': [J('提出を開く', 'Open the submission'), J('採点する', 'Grade'), J('返却する', 'Return')], 'outcomes': ['OUT-02'], 'basis': 'stated'},
            {'id': 'CUJ-03', 'name': J('提出の失敗の調査', 'Investigate a failed submission'), 'users': ['USR-03'],
             'user_goal': J('提出できなかった原因を早く突き止めて直す', 'Find and fix the cause of a failed submission quickly'),
             'steps': [J('知らせを受ける', 'Get notified'), J('ログをたどる', 'Trace the logs'), J('原因を直す', 'Fix the cause')], 'outcomes': [],
             'basis': 'inferred', 'basis_note': J('手順は推定', 'The steps are inferred')},
            {'id': 'CUJ-04', 'name': J('月次の提出状況の確認', 'Check monthly submissions'), 'users': ['USR-04', 'USR-02'],
             'user_goal': J('未提出の生徒を月ごとに確かめ、声をかける', 'Find the students who have not submitted each month, and contact them'),
             'steps': [J('レポートを開く', 'Open the report'), J('未提出の生徒を確かめる', 'Find the students who have not submitted')],
             'outcomes': ['OUT-01'], 'basis': 'stated'},
        ],
        'hints': [{'statement': J('生徒の個人情報を扱う', "Handles students' personal information"), 'kind': 'law', 'source': SRC}],
        'operational_facts': [
            {'id': 'OPF-01', 'fact': J('提出は締め切り前の 24 時間に集まる', 'Submissions peak in the 24 hours before the deadline'),
             'source': SRC, 'basis': 'stated'},
            {'id': 'OPF-02', 'fact': J('サーバーのアクセスログと夜間のジョブの記録がすでにある', 'Server access logs and records of the nightly jobs already exist'),
             'source': SRC, 'basis': 'stated'},
        ],
    }

    def qiu(i, title, user, cuj, outs, char, statement, failure, num, den, narrowed, kpi, observable=True, status='active', **kw):
        d = common(i, title, **kw)
        d['status'] = status
        d.update({'user': user, 'cuj': cuj, 'outcomes': outs, 'need': statement,
                  'context_of_use': {'device': J('スマートフォン', 'Smartphone'), 'network': None, 'user_type': None, 'task': title,
                                     'environment': None, 'other': None},
                  'characteristic': char, 'statement': statement, 'failure_scenario': failure,
                  'measure': {'numerator': num, 'denominator': den, 'narrowed_to': narrowed, 'denominator_needed_only': None,
                              'contribution': None, 'observable': observable, 'compared_with': None, 'scale': 'ratio'},
                  'kpi': kpi, 'target': None, 'target_status': 'undecided'})
        return d

    D['qiu'] = [
        qiu('QIU-01', J('期限までに提出が終わる', 'Submission finishes by the deadline'), 'USR-01', 'CUJ-01', ['OUT-01'], 'effectiveness',
            J('生徒はスマートフォンからでも、期限までに課題の提出を終えられる。', 'Students can finish submitting homework by the deadline, even from a smartphone.'),
            J('締め切り直前に提出が失敗し、期限に間に合わない。', 'A submission fails just before the deadline and misses it.'),
            J('提出が完了した課題', 'Homework submissions completed'), J('提出を始めた課題', 'Homework submissions started'),
            J('スマートフォン、締め切り前の 24 時間（OPF-01）', 'Smartphone, the 24 hours before the deadline (OPF-01)'), 'KPI-01', premises=['OPF-01']),
        qiu('QIU-02', J('提出したことを確かめられる', 'Can confirm the submission'), 'USR-01', 'CUJ-01', [], 'satisfaction > trust',
            J('生徒は、提出した課題が講師に届いたことをその場で確かめられる。', 'Students can confirm on the spot that their homework reached the teacher.'),
            J('受領の表示がなく、生徒が同じ課題を何度も出し直す。', 'With no receipt shown, students submit the same homework again and again.'),
            J('受領の表示を見た提出', 'Submissions where the receipt was seen'), J('完了した提出', 'Completed submissions'),
            J('すべての提出', 'All submissions'), None, observable=False),
        qiu('QIU-03', J('3 日以内に返る', 'Returned within 3 days'), 'USR-02', 'CUJ-02', ['OUT-02'], 'efficiency',
            J('講師は、提出から 3 日以内に採点して返却できる。', 'Teachers can grade and return a submission within 3 days of receiving it.'),
            J('採点の画面が重く、返却が週をまたぐ。', 'The grading screen is slow, and returns slip into the next week.'),
            J('3 日以内に返却した提出', 'Submissions returned within 3 days'), J('返却した提出', 'Returned submissions'),
            J('講師が担当する通常の課題', 'Regular homework the teacher is in charge of'), 'KPI-02'),
        qiu('QIU-04', J('失敗の原因を 30 分で特定する', 'Find the cause of a failure in 30 minutes'), 'USR-03', 'CUJ-03', [], 'efficiency',
            J('開発者は、提出の失敗の原因を知らせから 30 分以内に特定できる。', 'Developers can find the cause of a failed submission within 30 minutes of being notified.'),
            J('失敗した提出の経路がたどれず、原因の特定に半日かかる。', 'The path of a failed submission cannot be followed, and finding the cause takes half a day.'),
            J('30 分以内に原因を特定した失敗', 'Failures whose cause was found within 30 minutes'), J('調査した失敗', 'Failures investigated'),
            J('本番の失敗の知らせ', 'Notifications of failures in production'), None,
            basis='assumed', note=J('知らせに応じる時間帯は QAS-01 の仮定', 'When developers respond rests on QAS-01'), premises=['QAS-01']),
        qiu('QIU-05', J('月次の数字が提出と合う', 'Monthly numbers match the submissions'), 'USR-04', 'CUJ-04', ['OUT-01'],
            'freedom from risk > economic risk mitigation',
            J('塾の事務は、月次のレポートの件数が実際の提出の記録と一致していると信じて使える。',
              'The cram school office can trust that the counts in the monthly report match the actual submission records.'),
            J('未提出の生徒を取り違え、提出した生徒に催促する。', 'The office mixes up who has not submitted, and chases students who did.'),
            J('提出の記録と一致した月次の件数', 'Monthly counts that match the submission records'), J('月次の件数', 'Monthly counts'),
            J('月末の締め', 'The month-end close'), None),
        qiu('QIU-06', J('保護者に提出を知らせる', 'Tell parents about submissions'), 'USR-05', 'CUJ-01', [], 'effectiveness',
            J('保護者は提出を知れる。', 'Parents can know about submissions.'), J('保護者が提出を知らない。', 'Parents do not know about submissions.'),
            J('知らせた提出', 'Submissions notified'), J('提出', 'Submissions'), '—', None, status='retired'),
    ]

    def kpi(i, title, out, num, den, overlaps):
        d = common(i, title)
        d.update({'outcome': out, 'numerator': num, 'denominator': den, 'counted_over': J('すべての生徒と端末', 'All students and devices'),
                  'observable': True, 'overlaps_with': overlaps, 'overlap_note': None, 'target': None, 'target_status': 'undecided'})
        return d

    D['kpi'] = [
        kpi('KPI-01', J('提出完了率', 'Submission completion rate'), 'OUT-01', J('提出が完了した課題', 'Homework submissions completed'),
            J('提出を始めた課題', 'Homework submissions started'), ['QIU-01']),
        kpi('KPI-02', J('3 日以内の返却率', 'Return-within-3-days rate'), 'OUT-02', J('3 日以内に返却した提出', 'Submissions returned within 3 days'),
            J('返却した提出', 'Returned submissions'), ['QIU-03'])]

    def fr(i, title, origin, cuj, step, traces, statement, ac, interface, existing=False, proposal=None, status='active', **kw):
        d = common(i, title, **kw)
        d['status'] = status
        d.update({'statement': statement, 'origin': origin, 'cuj': cuj, 'cuj_step': step, 'traces_to': traces, 'proposal': proposal,
                  'existing': existing, 'extends': None, 'interface': interface, 'acceptance_criteria': ac, 'quality_hints': []})
        return d

    student, teacher = J('画面: 生徒', 'screen: student'), J('画面: 講師', 'screen: teacher')
    office = J('レポート: 塾の事務', 'report: cram school office')
    submit, attach = J('提出する', 'Submit'), J('ファイルを添付する', 'Attach a file')
    give_back, trace_logs = J('返却する', 'Return'), J('ログをたどる', 'Trace the logs')
    D['fr'] = [
        fr('FR-01', J('課題の提出', 'Homework submission'), 'cuj-step', 'CUJ-01', submit, ['QIU-01', 'KPI-01'],
           J('システムは、生徒が添付したファイルを課題への提出として受け付ける。', 'The system accepts the files a student attached as a submission for the assignment.'),
           [J('期限までに提出すると、提出の記録を作り「提出しました」と示す。', 'A submission made by the deadline creates a submission record and shows "Submitted".'),
            J('期限を過ぎた提出は、遅れの印を付けて受け付ける。', 'A submission after the deadline is accepted and marked late.')],
           [student, 'EXT-01'], existing=True, basis='stated', premises=['EXT-01']),
        fr('FR-02', J('受領の表示', 'Receipt display'), 'quality-in-use', 'CUJ-01', submit, ['QIU-02'],
           J('システムは、提出を受け付けると、受領の番号と時刻を生徒に示す。', 'When the system accepts a submission, it shows the student a receipt number and time.'),
           [J('提出の直後に受領の番号と時刻を示す。', 'The receipt number and time are shown right after submitting.'),
            J('提出の履歴から、過去の受領を開ける。', 'Past receipts can be opened from the submission history.')], [student],
           basis='confirmed', note=J('過去の受領を開けることは第 2 段階の質問 3 で確かめた（QAS-02）',
                                     'That past receipts can be opened was confirmed in stage 2, question 3 (QAS-02)'), premises=['QAS-02']),
        fr('FR-03', J('採点と返却', 'Grading and returning'), 'cuj-step', 'CUJ-02', give_back, ['QIU-03', 'KPI-02'],
           J('システムは、講師が点と講評を付けた提出を生徒に返却する。', 'The system returns to the student a submission that the teacher has scored and commented on.'),
           [J('返却すると、生徒の画面に点と講評を示す。', "On return, the score and comments appear on the student's screen.")], [teacher, student]),
        fr('FR-04', J('失敗した提出の追跡', 'Following a failed submission'), 'quality-in-use', 'CUJ-03', trace_logs, ['QIU-04'],
           J('システムは、失敗した提出について、受け付けてから失敗するまでに通った処理を順にたどれる記録を残す。',
             'For a failed submission, the system keeps a record of every step it went through, in order, from being received to failing.'),
           [J('失敗した提出を一つ選ぶと、通った処理と失敗した処理が順に示される。',
              'Choosing a failed submission shows, in order, the steps it went through and the one that failed.')], [J('画面: 開発者', 'screen: developer')]),
        fr('FR-05', J('夜間の提出状況レポート', 'Nightly submission report'), 'cuj-step', 'CUJ-04', J('レポートを開く', 'Open the report'), ['QIU-05'],
           J('システムは、毎晩、前日までの提出状況をまとめたレポートを作る。', 'Every night, the system builds a report of the submissions up to the previous day.'),
           [J('毎朝 6:00 までに、生徒ごとの提出と未提出の件数をレポートに示す。',
              'By 6:00 every morning, the report shows the numbers of submitted and missing homework per student.')], [office]),
        fr('FR-06', J('下書きの自動保存', 'Draft autosave'), 'proposal', 'CUJ-01', attach, ['QIU-01'],
           J('システムは、添付したファイルを提出の前に下書きとして保存する。', 'The system saves attached files as a draft before submission.'),
           [J('通信が切れても、添付したファイルが下書きに残る。', 'Attached files stay in the draft even if the connection drops.')], [student, 'EXT-01'],
           proposal='FRP-01', premises=['EXT-01']),
        fr('FR-07', J('一括ダウンロード', 'Bulk download'), 'cuj-step', 'CUJ-02', J('提出を開く', 'Open the submission'), ['QIU-03'],
           J('システムは、提出をまとめてダウンロードさせる。', 'The system lets teachers download submissions in bulk.'), ['—'], [teacher], status='retired'),
        fr('FR-08', J('返却の通知', 'Return notification'), 'cuj-step', 'CUJ-02', give_back, ['QIU-03'],
           J('システムは、返却したことを生徒に通知する。', 'The system notifies the student that the homework was returned.'),
           [J('返却すると、生徒に通知が届く。', 'On return, the student gets a notification.')], [J('通知: 生徒', 'notification: student')]),
        # acts across CUJs: no cuj and no cuj_step
        fr('FR-09', J('試験の提出を数えない', 'Leave test submissions out of the counts'), 'quality-in-use', None, None, ['QIU-01', 'QIU-05', 'KPI-01'],
           J('システムは、試験用のアカウントからの提出を、提出の件数と月次の件数に数えない。',
             'The system leaves submissions from test accounts out of the submission counts and the monthly counts.'),
           [J('試験用のアカウントで提出しても、月次のレポートの件数は変わらない。',
              'A submission from a test account does not change the counts in the monthly report.')], [office]),
    ]

    def frp(i, title, status, origin, statement, resolution):
        return {'id': i, 'title': title, 'status': status, 'basis': 'inferred', 'basis_note': None, 'premises': [],
                'proposed_by': 'functional-requirements-to-product-quality', 'origin': origin, 'changes': None,
                'reason': statement, 'suggested_statement': statement, 'affects': [], 'placeholders': [], 'resolution': resolution}

    D['frp'] = [
        frp('FRP-01', J('下書きの自動保存', 'Draft autosave'), 'accepted', ['QR-06'], J('添付したファイルを下書きとして保存する', 'Save attached files as a draft'),
            J('FR-06 として受け入れた', 'Accepted as FR-06')),
        frp('FRP-02', J('提出の自動の再送', 'Automatic resend of submissions'), 'rejected', ['QR-01'],
            J('失敗した提出を自動で送り直す', 'Resend failed submissions automatically'),
            J('FR-06 の下書きで足りるため受け入れない', 'Not accepted: the FR-06 draft is enough'))]

    def qr(i, title, model, layer, char, applies, traces, statement, failure, score, handling, reason=None, internal=(), entry=None,
           status='active', stakeholders=('USR-01',), **kw):
        d = common(i, title, **kw)
        d['status'] = status
        d.update({'model': model, 'layer': layer, 'characteristic': char, 'statement': statement, 'applies_to': applies, 'traces_to': traces,
                  'entry_point': entry, 'stakeholders': list(stakeholders), 'failure_scenario': failure,
                  'score': {'impact': score[0], 'likelihood': score[1]} if score else None, 'handling': handling, 'handling_reason': reason,
                  'implies_internal': list(internal), 'conflicts': [], 'stated_numbers': [], 'placeholders': []})
        return d

    D['qr'] = [
        qr('QR-01', J('提出の可用性', 'Submission availability'), 'product', 'external', 'reliability > availability', ['FR-01'], ['QIU-01'],
           J('生徒は締め切り前の混雑時にも提出できる。', 'Students can submit even in the rush before the deadline.'),
           J('締め切り直前に提出の画面がエラーになる。', 'The submission screen fails just before the deadline.'), (5, 3), 'emphasized', internal=['QR-05'],
           premises=['OPF-01']),
        qr('QR-02', J('提出の応答の速さ', 'Submission response time'), 'product', 'external', 'performance efficiency > time behaviour', ['FR-01'], ['QIU-01'],
           J('提出の確定が、生徒を待たせない速さで終わる。', 'Confirming a submission finishes fast enough not to keep students waiting.'),
           J('提出の確定に時間がかかり、生徒が画面を閉じる。', 'Confirming takes long, and students close the screen.'), (3, 3), 'minimum-line'),
        qr('QR-03', J('受領の表示の正しさ', 'Correct receipts'), 'product', 'external', 'functional suitability > functional correctness', ['FR-02'], ['QIU-02'],
           J('受領の表示は、実際に保存した提出とだけ一致する。', 'A receipt is shown only for a submission that was actually saved.'),
           J('保存に失敗したのに受領を示す。', 'A receipt is shown although saving failed.'), (4, 2), 'emphasized', internal=['QR-05']),
        qr('QR-04', J('返却の通知の分かりやすさ', 'Clear return notifications'), 'product', 'external', 'usability > operability', ['FR-08'], ['QIU-03'],
           J('生徒は返却の通知から講評にすぐたどり着ける。', 'Students get from a return notification to the comments right away.'),
           J('通知から講評が開けず、生徒が講評を読まない。', 'The comments cannot be opened from the notification, and students do not read them.'),
           (2, 2), 'excluded',
           reason=J('今期は対象外: 通知の文面は講師が自分で書くため', 'Excluded (this cycle): teachers write the notification text themselves'),
           basis='confirmed', note=J('今期は対象外とすることは第 3 段階の質問 2 で決めた（QAS-04 は覆った）',
                                     'Excluded this cycle in stage 3, question 2 (QAS-04 was overturned)')),
        qr('QR-05', J('提出の処理の自動テスト', 'Automated tests of submission processing'), 'product', 'internal', 'maintainability > testability',
           ['FR-01', 'FR-02'], ['QIU-01', 'QIU-02'],
           J('提出と受領の処理は、自動テストで振る舞いを確かめられる。', 'The behaviour of submission and receipt processing can be checked by automated tests.'),
           None, None, 'minimum-line'),
        qr('QR-06', J('ストレージの障害への耐性', 'Tolerance of storage failures'), 'product', 'external', 'reliability > fault tolerance', ['FR-01', 'FR-06'], ['QIU-01'],
           J('外部のストレージ（EXT-01）が一時的に失敗しても、添付したファイルを失わない。',
             'Attached files are not lost even when the external storage (EXT-01) fails for a while.'),
           J('ストレージの失敗で添付が消え、生徒が作り直す。', 'A storage failure loses the attachment, and the student has to redo it.'), (4, 2), 'emphasized',
           premises=['EXT-01']),
        qr('QR-07', J('提出の記録の完全性', 'Completeness of submission records'), 'data', 'data-inherent', 'completeness', ['FR-01', 'FR-05'], ['QIU-05'],
           J('提出の記録に、生徒、課題、時刻の欠けがない。', 'Submission records have no missing student, assignment or time.'),
           J('時刻の欠けた記録がレポートから漏れる。', 'Records missing a time drop out of the report.'), (4, 3), 'emphasized',
           stakeholders=('USR-01', 'USR-02', 'USR-04', 'EXT-01')),
        qr('QR-08', J('レポートの最新性', 'Currentness of the report'), 'data', 'data-inherent', 'currentness', ['FR-05'], ['QIU-05'],
           J('月次のレポートは、前日までの提出を毎朝反映している。', 'Every morning, the monthly report reflects the submissions up to the previous day.'),
           J('夜間の処理が遅れ、古い未提出の一覧で催促する。', 'The nightly job runs late, and students are chased from an old list.'), (3, 2), 'minimum-line',
           stakeholders=('USR-04', 'USR-02')),
        qr('QR-09', J('生徒の個人情報の機密性', "Confidentiality of students' personal information"), 'product', 'external', 'security > confidentiality',
           ['FR-01', 'FR-03'], [],
           J('生徒の氏名と提出物は、担当の講師と本人のほかに見えない。', "Students' names and submissions are visible only to the student and the teacher in charge."),
           J('他の生徒の提出物が見える。', "Another student's submission is visible."), (5, 2), 'emphasized',
           reason=J('法令から来る要求なので点に関わらず残す。', 'It comes from a law, so it stays whatever its score.'),
           entry={'type': 'law', 'source': J('個人情報の保護に関する法律。生徒の氏名と提出物を扱う',
                                             "Act on the Protection of Personal Information. The service handles students' names and submissions"),
                  'brought_by': J('開発の責任者', 'Head of development')}),
        qr('QR-10', J('失敗をたどれること', 'Traceable failures'), 'product', 'external', 'maintainability > analysability', ['FR-04'], ['QIU-04'],
           J('開発者は、提出の失敗を 1 件ずつ、通った処理をまたいでたどれる。', 'Developers can follow each failed submission across the steps it went through.'),
           J('失敗した提出の経路がたどれず、原因を特定できない。', 'The path of a failed submission cannot be followed, and the cause cannot be found.'),
           (3, 3), 'minimum-line', stakeholders=('USR-03',), basis='assumed', premises=['QAS-01']),
        qr('QR-11', J('古い要求', 'Old requirement'), 'product', 'external', 'usability > learnability', ['FR-01'], ['QIU-01'], '—', '—', (1, 1), 'excluded',
           status='retired'),
        qr('QR-12', J('採点の正確さ', 'Correct grading'), 'product', 'external', 'functional suitability > functional correctness', ['FR-03'], ['QIU-03'],
           J('返却した点は、講師が付けた点と一致する。', 'The returned score matches the score the teacher gave.'),
           J('点の保存を誤り、違う点が返る。', 'Saving the score goes wrong, and a different score is returned.'), (4, 2), 'emphasized',
           stakeholders=('USR-01', 'USR-02')),
        qr('QR-13', J('提出の復元', 'Restoring submissions'), 'data', 'data-system-dependent', 'recoverability', ['FR-01'], [],
           J('提出から 1 年は、消えた提出を復元できる。', 'A lost submission can be restored for a year after it was made.'),
           J('ストレージの障害で提出が消え、成績の根拠を失う。', 'A storage failure loses submissions, and with them the evidence for grades.'), (3, 1), 'minimum-line',
           reason=J('開発方針から来る要求なので点に関わらず残す。', 'It comes from a development policy, so it stays whatever its score.'),
           entry={'type': 'policy', 'source': J('開発方針: 提出は 1 年間保管する', 'Development policy: keep submissions for a year'),
                  'brought_by': J('プロダクトオーナー', 'Product owner')},
           stakeholders=('USR-01', 'EXT-01'), premises=['EXT-01']),
    ]

    def nfr(i, title, frm, kind, cuj, statement, slo=None, gate=None, audit=None, monitor=None, **kw):
        d = common(i, title, **kw)
        d.update({'from': frm, 'kind': kind, 'cuj': cuj, 'statement': statement,
                  'conditions': {'workload': J('締め切り前の 24 時間の集中まで（OPF-01）', 'Up to the rush in the 24 hours before a deadline (OPF-01)'),
                                 'users': J('生徒と講師。試験用のアカウントを除く', 'Students and teachers, test accounts excluded'),
                                 'transactions': J('提出', 'Submissions')},
                  'slo': slo, 'gate': gate, 'audit': audit, 'monitor': monitor})
        return d

    alerts = [{'notify': 'page', 'long_window': '1h', 'short_window': '5m', 'burn_rate': 14.4, 'budget_spent_at_alert': '2.1%', 'condition': None},
              {'notify': 'ticket', 'long_window': '3d', 'short_window': '6h', 'burn_rate': 1, 'budget_spent_at_alert': '10.7%', 'condition': None}]
    D['nfr'] = [
        nfr('NFR-01', J('提出の可用性の SLO', 'Submission availability SLO'), ['QR-01', 'QR-06'], 'slo', 'CUJ-01',
            J('直近 28 日で、有効な提出の 99.5% が、システムの失敗なしに受け付けられる。',
              'Over a rolling 28 days, 99.5% of valid submissions are accepted without a failure of the system.'),
            slo={'sli': 'SLI-01', 'target': '99.5%', 'target_status': 'confirmed',
                 'target_rationale': J('第 4 段階の質問 1 で、塾の事務と講師が確かめた', 'Confirmed by the office and the teachers in stage 4, question 1'),
                 'window': '28-day rolling', 'error_budget': J('有効な提出の 0.5% までが失敗してよい', 'Up to 0.5% of valid submissions may fail'),
                 'error_budget_volume': J('28 日の提出の件数 × 0.005', 'Submissions in 28 days × 0.005'), 'policy': 'EBP-01', 'alerts': alerts},
            basis='confirmed', premises=['OPF-01']),
        nfr('NFR-02', J('夜間レポートの締め切りの SLO', 'Nightly report deadline SLO'), ['QR-08'], 'slo', 'CUJ-04',
            J('直近 28 日で、夜間レポートの 99% が毎朝 6:00 までに終わる。', 'Over a rolling 28 days, 99% of nightly reports finish by 6:00 in the morning.'),
            slo={'sli': 'SLI-02', 'target': '99%', 'target_status': 'provisional',
                 'target_rationale': J('運用の実績がないので仮に採った（QAS-03）', 'Adopted provisionally, as there is no operating history (QAS-03)'),
                 'window': '28-day rolling',
                 'error_budget': J('28 日のうち 1% までの夜は 6:00 を過ぎてよい', 'Up to 1% of the nights in 28 days may finish after 6:00'),
                 'error_budget_volume': J('28 日で 0.28 回（1 回でも遅れると使い切る）', '0.28 runs in 28 days (one late run uses it all)'),
                 'policy': 'EBP-02', 'bad_run_budget_share': J('1 回の遅れでバジェットの 357%', 'One late run uses 357% of the budget'),
                 'progress_alert': J('NFR-05（5:30 に終わっていなければ知らせる）', 'NFR-05 (notifies if the report has not finished at 5:30)'),
                 'after_miss': 'ticket'},
            basis='assumed', premises=['QAS-03']),
        nfr('NFR-03', J('受領の表示の E2E テスト', 'Receipt E2E test'), ['QR-03'], 'gate', 'CUJ-01',
            J('提出から受領の表示までを E2E テストで確かめ、失敗したら配備を止める。',
              'An E2E test checks everything from submitting to the receipt, and a failure stops the deploy.'),
            gate={'where': 'CI', 'check': J('提出から受領の表示までの E2E テスト', 'E2E test from submitting to the receipt'),
                  'threshold': J('失敗 0 件', '0 failures')}),
        nfr('NFR-04', J('提出の処理のテストの網羅', 'Test coverage of submission processing'), ['QR-05'], 'gate', 'CUJ-01',
            J('提出と受領の処理の分岐を、自動テストで 80% 以上網羅する。', 'Automated tests cover at least 80% of the branches of submission and receipt processing.'),
            gate={'where': 'definition-of-done', 'check': J('提出と受領の処理の分岐の網羅', 'Branch coverage of submission and receipt processing'),
                  'threshold': '80%'}),
        nfr('NFR-05', J('夜間レポートの進み具合', 'Nightly report progress'), ['QR-08'], 'monitor', 'CUJ-04',
            J('夜間レポートが 5:30 に終わっていなければ開発者に知らせる。', 'Notify the developers if the nightly report has not finished at 5:30.'),
            monitor={'signal': J('レポートの処理の終了の記録', 'The end record of the report job'),
                     'threshold': J('5:30 に終わっていない', 'Not finished at 5:30'), 'notifies': J('開発者（チャット）', 'Developers (chat)')}),
        nfr('NFR-06', J('提出の応答の遅さの監視', 'Slow submission monitor'), ['QR-02'], 'monitor', 'CUJ-01',
            J('提出の確定の 95 パーセンタイルが 3 秒を超えたら知らせる。', 'Notify when the 95th percentile of submission confirmation exceeds 3 seconds.'),
            monitor={'signal': J('提出の確定にかかった時間', 'Time taken to confirm a submission'),
                     'threshold': J('95 パーセンタイルが 3 秒を超えて 1 時間続く', 'The 95th percentile stays above 3 seconds for an hour'),
                     'notifies': J('開発者（チケット）', 'Developers (ticket)')}),
        nfr('NFR-07', J('提出の記録の欠けの監視', 'Missing-record monitor'), ['QR-07'], 'monitor', 'CUJ-04',
            J('時刻か生徒の欠けた提出の記録が見つかったら、その日のうちに知らせる。',
              'Notify on the same day when a submission record missing a time or a student is found.'),
            monitor={'signal': J('毎晩の記録の確かめ', 'The nightly record check'), 'threshold': J('欠け 1 件', '1 missing value'),
                     'notifies': J('開発者と塾の事務', 'Developers and the cram school office')}),
        nfr('NFR-08', J('個人情報の扱いの監査', 'Personal information audit'), ['QR-09'], 'audit', None,
            J('半年ごとに、提出物を見られる権限を棚卸しする。', 'Every six months, review who can see submissions.'),
            audit={'mechanism': J('アクセス権の棚卸し', 'Access review'), 'criterion': J('不要な権限 0 件', '0 unneeded permissions'),
                   'cadence_or_deadline': J('半年ごと', 'Every six months')}),
        nfr('NFR-09', J('失敗をたどれることの完成の定義', 'Traceability in the Definition of Done'), ['QR-10'], 'gate', 'CUJ-03',
            J('提出の経路の処理は、失敗した提出をたどれる記録を残すまで完成としない。',
              'A step on the submission path is not done until it leaves a record that lets a failed submission be followed.'),
            gate={'where': 'definition-of-done', 'check': J('失敗した提出をその処理までたどれること', 'A failed submission can be followed to that step'),
                  'threshold': J('提出の経路のすべての処理', 'Every step on the submission path')},
            basis='assumed', premises=['QAS-01']),
        nfr('NFR-10', J('採点の二重確認', 'Double-check of grading'), ['QR-12'], 'gate', 'CUJ-02',
            J('採点の保存を変える変更は、リリース前に点の一致を確かめる。', 'A change to how scores are saved is checked before release for matching scores.'),
            gate={'where': 'release-check', 'check': J('保存した点と入力した点の一致', 'Saved scores match entered scores'),
                  'threshold': J('不一致 0 件', '0 mismatches')}),
        nfr('NFR-11', J('復元の訓練', 'Restore drill'), ['QR-13'], 'audit', None,
            J('年に一度、消した提出を復元する訓練をする。', 'Once a year, rehearse restoring a deleted submission.'),
            audit={'mechanism': J('復元の訓練', 'Restore drill'), 'criterion': J('1 時間以内に復元できる', 'Restored within an hour'),
                   'cadence_or_deadline': J('毎年 3 月', 'Every March')}),
    ]

    def sli(i, title, refs, func, entity, unit_event, vantage, reason, elements, blind):
        d = common(i, title, premises=['OPF-02'])
        d.update({'function': func, 'refs': refs, 'reshaped': None, 'target_entity': entity, 'purpose': title, 'unit_event': unit_event,
                  'vantage': vantage, 'vantage_reason': reason, 'existing_source': 'OPF-02', 'elements': elements, 'scale': 'ratio',
                  'applicability': J('本番', 'Production'), 'lifecycle': J('本番で測る', 'Measured in production'), 'blind_spots': blind})
        return d

    D['sli'] = [
        sli('SLI-01', J('提出の可用性', 'Submission availability'), ['QR-01', 'NFR-01'], 'OK ÷ VALID',
            J('提出を受け付けてから結果を返すまでのシステムの扱い', 'The submission as the system handles it, from receiving it to answering'),
            J('生徒が送った提出 1 件', 'One submission a student sends'), 'system-boundary',
            J('失敗したかどうかは受け付けた側で数えられる。生徒の端末の中の失敗は別の SLI にする',
              "Whether it failed can be counted where it is received; failures on the student's device are a separate SLI"),
            {'VALID': {'definition': J('ログインした生徒が送った提出', 'Submissions sent by signed-in students'),
                       'exclusions': J('試験用のアカウント', 'Test accounts'), 'unit': J('提出', 'submissions'),
                       'counting_rule': J('送り直した提出は 1 件と数える', 'A submission sent again counts once')},
             'OK': {'definition': J('VALID のうち、システムが失敗を返さなかった提出', 'Submissions in VALID that the system did not fail'),
                    'unit': J('提出', 'submissions'), 'counting_rule': J('VALID と同じ', 'Same as VALID')}},
            J('システムに届かなかった提出は見えない', 'Submissions that never reach the system are not visible')),
        sli('SLI-02', J('夜間レポートの締め切り', 'Nightly report deadline'), ['QR-08', 'NFR-02'], 'ON_TIME ÷ RUNS',
            J('前日までの提出をまとめた夜間レポート', 'The nightly report of the submissions up to the previous day'),
            J('予定した夜間レポートの実行 1 回', 'One scheduled run of the nightly report'), 'data',
            J('事務が見るのはレポートの中身なので、レポートがいつ揃ったかで数える', 'The office reads the report itself, so it is counted by when the report was complete'),
            {'RUNS': {'definition': J('予定した夜間レポートの実行', 'Scheduled runs of the nightly report'), 'unit': J('回', 'runs'),
                      'counting_rule': J('1 晩 1 回', 'One per night')},
             'ON_TIME': {'definition': J('RUNS のうち、6:00 までにレポートが揃ったもの', 'Runs in RUNS whose report was complete by 6:00'),
                         'unit': J('回', 'runs'), 'counting_rule': J('RUNS と同じ', 'Same as RUNS')}},
            J('レポートの中身の誤りは見えない（QR-07 の監視で見る）', 'Errors inside the report are not visible (the QR-07 monitor watches them)')),
    ]
    D['ebp'] = [
        dict(common('EBP-01', J('提出の SLO のエラーバジェット方針', 'Error budget policy for the submission SLO'), basis='confirmed'),
             applies_to=['NFR-01'],
             rules=[{'when': J('残りのバジェットが 50% を下回った', 'Less than 50% of the budget remains'),
                     'action': J('次のスプリントは信頼性の作業を先にする', 'The next sprint puts reliability work first')},
                    {'when': J('バジェットを使い切った', 'The budget is used up'),
                     'action': J('ウィンドウの残りは修正だけを出す', 'Only fixes ship for the rest of the window')},
                    {'when': J('締め切り前の 24 時間', 'The 24 hours before a deadline'),
                     'action': J('提出に関わる配備をしない', 'No deploys that touch submissions')}]),
        dict(common('EBP-02', J('データの SLO のエラーバジェット方針', 'Error budget policy for the data SLO'), basis='confirmed'),
             applies_to=['NFR-02'],
             rules=[{'when': J('レポートが 6:00 に間に合わなかった', 'The report missed 6:00'),
                     'action': J('原因を直す作業と、その朝の催促の取り消しを起票する', "File tickets to fix the cause and to cancel that morning's reminders")},
                    {'when': J('同じ月に 2 回遅れた', 'Late twice in the same month'),
                     'action': J('夜間の処理の見直しを次のスプリントで先にする', 'The next sprint puts a review of the nightly job first')}]),
    ]

    def qas(i, title, status, stage, kind, statement, why, breadth, severity, note, answer=None, where=None):
        return {'id': i, 'title': title, 'status': status, 'stage': stage, 'kind': kind, 'statement': statement, 'why_unsure': why,
                'breadth': breadth, 'severity': severity, 'rating_note': note, 'answer': answer, 'answered_in': where}

    D['qas'] = [
        qas('QAS-01', J('開発者は締め切り前の 24 時間も知らせに応じる', 'Developers answer notifications in the 24 hours before a deadline'), 'open', 1,
            'judgment', J('開発者は、締め切り前の 24 時間は夜でも提出の失敗の知らせに応じる。',
                          'Developers answer failure notifications in the 24 hours before a deadline, at night included.'),
            J('入力は 30 分を示すが、いつ応じるかは示さない。', 'The input gives the 30 minutes but not when developers are on call.'), 'low', 'medium',
            J('QIU-04 とそこから導く項目だけが頼る。', 'Only QIU-04 and the items derived from it depend on it.')),
        qas('QAS-02', J('過去の受領を後から開ける', 'Past receipts can be opened later'), 'confirmed', 2, 'judgment',
            J('生徒は、提出の履歴から過去の受領を開ける。', 'Students can open past receipts from their submission history.'),
            J('入力は受領の表示を求めるが、後から見るかは示さない。', 'The input asks for a receipt but not whether it can be seen later.'), 'low', 'low',
            J('FR-02 だけが頼る。', 'Only FR-02 depends on it.'), answer=J('開ける', 'Yes, they can'), where=J('第 2 段階、質問 3', 'stage 2, question 3')),
        qas('QAS-03', J('夜間レポートの目標値を 99% とする', 'The nightly report target is 99%'), 'open', 4, 'decision',
            J('夜間レポートが 6:00 に揃う割合の目標値を、仮に 99% とする。', 'The share of nightly reports complete by 6:00 is provisionally set at 99%.'),
            J('運用の実績がなく、事務が何回の遅れまで許すかを聞いていない。', 'There is no operating history, and the office was not asked how many late reports it accepts.'),
            'low', 'medium', J('NFR-02 と EBP-02 だけが頼る。', 'Only NFR-02 and EBP-02 depend on it.')),
        qas('QAS-04', J('返却の通知の文面を固定する', 'Return notifications use a fixed text'), 'overturned', 3, 'judgment',
            J('返却の通知は、システムが決めた文面で送る。', 'Return notifications are sent with a text the system sets.'),
            J('入力は通知を求めるが、文面を誰が書くかは示さない。', 'The input asks for notifications but not who writes their text.'), 'low', 'low',
            J('QR-04 だけが頼る。', 'Only QR-04 depends on it.'), answer=J('講師が自分で書く', 'Teachers write it themselves'),
            where=J('第 3 段階、質問 2', 'stage 3, question 2')),
    ]

    def head(title, n):
        day, base = HEAD[n]
        return J('# %s: 課題提出サービス\n\n状態: 回答反映済み · 更新: %s · 入力の基準: %s · 第 %d 段階（全 4 段階）\n',
                 '# %s: Homework submission service\n\nStatus: answers applied · Updated: %s · Inputs as of: %s · Stage %d of 4\n') % (
            title, day, base or J('なし', 'none'), n)

    D['report1'] = head(J('利用時の品質と KPI', 'Quality in use and KPIs'), 1) + J('''
## 利用時の品質要求

### 対象にしない

| CUJ | 特性 | 理由 |
|---|---|---|
| CUJ-01〜03 | 満足性 > 快感性 | 入力にこのニーズがなく、成果を損なう失敗のシナリオも書けない。 |
| CUJ-04 | 利用状況網羅性 > 柔軟性 | 事務の使い方は月末の確認の一つだけ。 |
''', '''
## Quality-in-use requirements

### Not targeted

| CUJs | Characteristics | Reason |
|---|---|---|
| CUJ-01–03 | Satisfaction > pleasure | The inputs have no such need, and no failure scenario that harms an outcome can be written. |
| CUJ-04 | Context coverage > flexibility | The office uses it in one way only: the month-end check. |
''')

    def report2(full):
        # Before stage 3 there is no FRP-01, so no FR-06 either
        f06 = J('FR-06', 'FR-06') if full else ''
        attach_row = J('| CUJ-01 | ファイルを添付する | %s | |', '| CUJ-01 | Attach a file | %s | |') % f06
        new01 = J('| QIU-01 | 新しい機能 | %s | %s |', '| QIU-01 | new function | %s | %s |') % (
            'FR-06, FR-09' if full else 'FR-09', J('FR-06 は FRP-01 から', 'FR-06 comes from FRP-01') if full else '')
        return head(J('機能要件', 'Functional requirements'), 2) + J('''
## CUJ の手順ごとの機能

| CUJ | 手順 | FR | 注記 |
|---|---|---|---|
| CUJ-01 課題の提出 | 課題を開く | | 今ある画面で足りる |
%s
| CUJ-01 | 提出する | FR-01, FR-02 | |
| CUJ-02 採点と返却 | 提出を開く | | |
| CUJ-02 | 採点する | | |
| CUJ-02 | 返却する | FR-03, FR-08 | |
| CUJ-03 提出の失敗の調査 | 知らせを受ける | | |
| CUJ-03 | ログをたどる | FR-04 | |
| CUJ-03 | 原因を直す | | 開発者がシステムの外で直す |
| CUJ-04 月次の提出状況の確認 | レポートを開く | FR-05 | |
| CUJ-04 | 未提出の生徒を確かめる | | 事務と講師がレポートを見て確かめる |

FR-09 は CUJ をまたいで働くので、どの手順にも置かない。

## 利用時の品質要求の対応

| QIU | 対応の仕方 | FR | 注記 |
|---|---|---|---|
| QIU-01 期限までに提出が終わる | 機能要件が品質として担う | FR-01 | |
%s
| QIU-02 提出したことを確かめられる | 新しい機能 | FR-02 | |
| QIU-03 3 日以内に返る | 機能要件が品質として担う | FR-03 | |
| QIU-04 失敗の原因を 30 分で特定する | 新しい機能 | FR-04 | |
| QIU-04 | データはほかから得る | | 原因を特定した時刻は、開発者の対応の記録で数える |
| QIU-05 月次の数字が提出と合う | 機能要件が品質として担う | FR-05 | |
| QIU-05 | 新しい機能 | FR-09 | |

## 検討して加えなかった機能

| 候補 | 対象 | 理由 |
|---|---|---|
| 提出の期限を自動で延ばす | QIU-01 | 期限は講師が決める（CON-01）。 |
| 採点の下書きを共有する | QIU-03 | 講師は一人で採点する。 |
''', '''
## Functions by CUJ step

| CUJ | Step | FRs | Note |
|---|---|---|---|
| CUJ-01 Submit homework | Open the assignment | | The current screen is enough |
%s
| CUJ-01 | Submit | FR-01, FR-02 | |
| CUJ-02 Grade and return | Open the submission | | |
| CUJ-02 | Grade | | |
| CUJ-02 | Return | FR-03, FR-08 | |
| CUJ-03 Investigate a failed submission | Get notified | | |
| CUJ-03 | Trace the logs | FR-04 | |
| CUJ-03 | Fix the cause | | Developers fix it outside the system |
| CUJ-04 Check monthly submissions | Open the report | FR-05 | |
| CUJ-04 | Find the students who have not submitted | | The office and the teachers read the report |

FR-09 acts across CUJs, so it is on no step.

## Quality-in-use coverage

| QIU | How it is covered | FRs | Note |
|---|---|---|---|
| QIU-01 Submission finishes by the deadline | an FR carries it as quality only | FR-01 | |
%s
| QIU-02 Can confirm the submission | new function | FR-02 | |
| QIU-03 Returned within 3 days | an FR carries it as quality only | FR-03 | |
| QIU-04 Find the cause of a failure in 30 minutes | new function | FR-04 | |
| QIU-04 | data comes from elsewhere | | When the cause was found is counted from the developers' incident records |
| QIU-05 Monthly numbers match the submissions | an FR carries it as quality only | FR-05 | |
| QIU-05 | new function | FR-09 | |

## Functions considered and not added

| Candidate | For | Reason |
|---|---|---|
| Extend the deadline automatically | QIU-01 | Teachers set the deadlines (CON-01). |
| Share grading drafts | QIU-03 | Each teacher grades alone. |
''') % (attach_row, new01)

    D['report2_full'], D['report2_stage2'] = report2(True), report2(False)
    D['report3'] = head(J('製品の品質とデータの品質', 'Product quality and data quality'), 3) + J('''
## 網羅の確認

CUJ-01: FR-01, FR-02, FR-06, FR-09。CUJ-02: FR-03, FR-08。CUJ-03: FR-04。CUJ-04: FR-05, FR-09。

### 製品の品質

| 特性 > 副特性 | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | 対象にしない理由 |
|---|---|---|---|---|---|
| 機能適合性 > 機能正確性 | QR-03 | QR-12 | — | — | CUJ-03、04: 結果を計算する機能がない |
| 性能効率性 > 時間効率性 | QR-02 | — | — | — | CUJ-02〜04: 待ち時間が成果を損なう場面がない |
| 使用性 > 運用操作性 | — | QR-04 | — | — | CUJ-01、03、04: 操作は一つの画面で終わる |
| 信頼性 > 可用性 | QR-01 | — | — | — | CUJ-02〜04: 締め切りの集中がない |
| 信頼性 > 障害許容性 | QR-06 | — | — | — | CUJ-02〜04: 外部のストレージを通らない |
| 保守性 > 解析性 | — | — | QR-10 | — | CUJ-01、02、04: 開発者の手順がない |

### データの品質

| 特性 | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | 対象にしない理由 |
|---|---|---|---|---|---|
| 完全性 | QR-07 | — | — | QR-07 | CUJ-02、03: 提出の記録を数えない |
| 最新性 | — | — | — | QR-08 | CUJ-01〜03: 前日までのまとめを見ない |

## 外部品質から導いた内部品質

| 外部の QR | 内部の QR | どう支えるか |
|---|---|---|
| QR-01、QR-03 | QR-05 | 提出と受領の処理を自動テストで確かめるので、壊れた変更を本番に出さない。 |
''', '''
## Coverage checklist

CUJ-01: FR-01, FR-02, FR-06, FR-09. CUJ-02: FR-03, FR-08. CUJ-03: FR-04. CUJ-04: FR-05, FR-09.

### Product quality

| Characteristic > sub-characteristic | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | Reason not targeted |
|---|---|---|---|---|---|
| Functional suitability > functional correctness | QR-03 | QR-12 | — | — | CUJ-03, 04: no function computes a result |
| Performance efficiency > time behaviour | QR-02 | — | — | — | CUJ-02–04: no wait harms an outcome |
| Usability > operability | — | QR-04 | — | — | CUJ-01, 03, 04: one screen does the task |
| Reliability > availability | QR-01 | — | — | — | CUJ-02–04: no deadline rush |
| Reliability > fault tolerance | QR-06 | — | — | — | CUJ-02–04: they do not go through the external storage |
| Maintainability > analysability | — | — | QR-10 | — | CUJ-01, 02, 04: no developer steps |

### Data quality

| Characteristic | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | Reason not targeted |
|---|---|---|---|---|---|
| Completeness | QR-07 | — | — | QR-07 | CUJ-02, 03: they do not count submission records |
| Currentness | — | — | — | QR-08 | CUJ-01–03: they do not read the summary up to the previous day |

## Internal quality derived from external quality

| External QR | Internal QR | How it supports the external one |
|---|---|---|
| QR-01, QR-03 | QR-05 | Automated tests check submission and receipt processing, so broken changes do not reach production. |
''')
    D['report4'] = head(J('非機能要件、SLI と SLO', 'Non-functional requirements, SLIs and SLOs'), 4) + J('''
## 割り当て

| QR | 扱い | 品質を支える機能 | 非機能要件 | 種類 | 範囲外 |
|---|---|---|---|---|---|
| QR-01 提出の可用性 | 重視 | — | NFR-01 | SLO | |
| QR-02 提出の応答の速さ | 最低限守る線 | — | NFR-06 | 監視 | |
| QR-03 受領の表示の正しさ | 重視 | — | NFR-03 | ゲート | |
| QR-05 提出の処理の自動テスト | 最低限守る線 | — | NFR-04 | ゲート | |
| QR-06 ストレージの障害への耐性 | 重視 | FR-06 | NFR-01 | SLO | |
| QR-07 提出の記録の完全性 | 重視 | — | NFR-07 | 監視 | |
| QR-08 レポートの最新性 | 最低限守る線 | — | NFR-02, NFR-05 | SLO、監視 | |
| QR-09 生徒の個人情報の機密性 | 重視 | — | NFR-08 | 監査 | |
| QR-10 失敗をたどれること | 最低限守る線 | FR-04 | NFR-09 | ゲート | |
| QR-12 採点の正確さ | 重視 | — | NFR-10 | ゲート | |
| QR-13 提出の復元 | 最低限守る線 | — | NFR-11 | 監査 | ストレージの事業者の障害そのもの |
''', '''
## Allocation

| QR | Handling | Supporting function | NFRs | Kind | Out of scope |
|---|---|---|---|---|---|
| QR-01 Submission availability | Emphasized | — | NFR-01 | SLO | |
| QR-02 Submission response time | Minimum line | — | NFR-06 | Monitor | |
| QR-03 Correct receipts | Emphasized | — | NFR-03 | Gate | |
| QR-05 Automated tests of submission processing | Minimum line | — | NFR-04 | Gate | |
| QR-06 Tolerance of storage failures | Emphasized | FR-06 | NFR-01 | SLO | |
| QR-07 Completeness of submission records | Emphasized | — | NFR-07 | Monitor | |
| QR-08 Currentness of the report | Minimum line | — | NFR-02, NFR-05 | SLO, monitor | |
| QR-09 Confidentiality of students' personal information | Emphasized | — | NFR-08 | Audit | |
| QR-10 Traceable failures | Minimum line | FR-04 | NFR-09 | Gate | |
| QR-12 Correct grading | Emphasized | — | NFR-10 | Gate | |
| QR-13 Restoring submissions | Minimum line | — | NFR-11 | Audit | Failures of the storage provider itself |
''')
    return D


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000), encoding='utf-8')


def write(dest, stage, lang):
    D = data(lang)
    if dest.exists():
        shutil.rmtree(dest)
    dump(dest / 'context.yaml', D['context'])
    for d in D['qiu']:
        dump(dest / 'qiu' / ('%s.yaml' % d['id']), d)
    for d in D['kpi']:
        dump(dest / 'kpi' / ('%s.yaml' % d['id']), d)
    for d in D['fr']:
        if stage < 3 and d['id'] == 'FR-06':
            continue
        dump(dest / 'fr' / ('%s.yaml' % d['id']), d)
    for d in D['qas']:
        if d['stage'] <= stage:
            dump(dest / 'qas' / ('%s.yaml' % d['id']), d)
    (dest / '1-quality-in-use.md').write_text(D['report1'], encoding='utf-8')
    (dest / '2-functional-requirements.md').write_text(D['report2_full'] if stage >= 3 else D['report2_stage2'], encoding='utf-8')
    if stage < 3:
        return
    for kind in ('frp', 'qr'):
        for d in D[kind]:
            dump(dest / kind / ('%s.yaml' % d['id']), d)
    (dest / '3-product-quality.md').write_text(D['report3'], encoding='utf-8')
    for kind in ('nfr', 'sli', 'ebp'):
        for d in D[kind]:
            dump(dest / kind / ('%s.yaml' % d['id']), d)
    (dest / '4-nfr-slo.md').write_text(D['report4'], encoding='utf-8')


CASES = [('homework-service-full', 4, 'ja'), ('homework-service-stage2', 2, 'ja'), ('homework-service-full-en', 4, 'en')]

if __name__ == '__main__':
    for case, stage, lang in CASES:
        write(ROOT / case / 'files' / 'docs' / 'quality', stage, lang)
    print('書き出し:', ' '.join(str(ROOT / c) for c, _, _ in CASES))

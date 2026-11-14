# 技術方針: 配車サービス

状態: 回答反映済み · 更新: 2026-11-13 · 入力の基準: c14d073 · 第 2b 段階（全 4 段階）

## 概要
配車サーバー（ELM-03）は Node.js 26 の上の TypeScript と Hono 4 で作り、ビルドせずに型を外して動かし、ELM-04 を Drizzle ORM で読み書きする。二つの Web アプリ（ELM-01、ELM-02）は React 19 を Vite で単一ページのアプリにし、React Router、TanStack Query、React Aria Components を使い、ELM-03 を、その仕様書から生成した型で呼ぶ。Web アプリは環境ごとの値をビルドに入れず、起動のときに ELM-03 から読む（DEC-34）。三つのコンポーネントは今のリポジトリ一つに置き、中を業務の機能ごとに分け、境を Oxlint の規則で守る。パイプラインは TC-09 のとおり開発者のマシンだけで動き、変更のたびの検査は git のフックが、リリースの前の確かめは版の印から起こすリリースの手順が、コンテナで立てる試験の環境で行う（DEC-32）。試験の環境と開発者のマシンは、ローカルの本番と別の秘密の値と外部のアカウントを使う。品質チェーンのゲート 19 はすべて出どころを、監査 4 はすべて置き場所を POL-03 で決め、品質チェーンへの要求はない。この実行は、第 2b 段階のレビューの指摘 FND-12〜FND-18（中 2、軽微 5）をすべて受け入れた。尋ねる点はなく、主な仮定は、開発者が主なライブラリを使いこなすか学べること（DAS-07）、開発者のマシンとテストに使う iPhone とそれに入れる iOS のベータ版（DAS-08）、人が行う確かめと監査を開発者が行うこと（DAS-09）。

## 入力
| 出どころ | 得たもの |
|---|---|
| docs/design/1-architecture-drivers.md、drv/ | DRV-01〜DRV-35（主なものは 12）。この段階の方針を形づくるのは、変更の DRV-12、DRV-13、原則の DRV-31、DRV-33、DRV-34、DRV-35、制約の DRV-15、DRV-16、DRV-17、DRV-18、DRV-22。試験の環境とローカルの本番の外部のアカウントを分けることは、品質の DRV-07 と観測の DRV-27 の測定量を守る |
| docs/design/2-architecture.md、elm/、dec/ | 要素 ELM-01〜ELM-12（コンポーネントは ELM-01、ELM-02、ELM-03）、DEC-01〜DEC-27、四つのビュー。第 2 段階がこの段階に任せた点（コードの分け方と CI の検査、ローカルの定期の呼び出しと HTTPS の証明書、試験のデータ、NFR-15 と NFR-16 の置き場所、記録した日ごとの鍵の読み方、作り方、捨て方、データの形を変える道具、配備と戻しの手順とその自動化、デモの回を開くときと閉じるときの手順の自動化、コードの中のエラーと秘密の値の扱い） |
| docs/design/design-context.yaml | TC-01〜TC-18、PC-01〜PC-03、TEAM-01、STK-01〜STK-04。今の構造はなく、すべて新規 |
| docs/design/reviews/2b-technical-policy.md、fnd/ | この段階に宛てた指摘は、第 2b 段階の全体のレビューが出した FND-12〜FND-18（中 2、軽微 5）。前の実行からの入力の変化は、このレビューとその指摘だけ |
| docs/design/das/、hnd/、qcr/、reviews/2-architecture.md | 未確認の DAS-01、DAS-02、DAS-04〜DAS-09 と、確認済みの DAS-03。この段階に宛てた申し送りはない（HND-01〜HND-13 は第 3 段階と第 4 段階、HND-14 はこの段階が第 4 段階に送ったもの）。FND-10 と FND-11 は第 2 段階に宛てたもの。品質チェーンへの要求 QCR-01（未回答）と QCR-02〜QCR-05（回答済み）は、この段階の項目を変えない |
| docs/quality/nfr/ | ゲート 19（NFR-09、NFR-11、NFR-13、NFR-15、NFR-21、NFR-22、NFR-25、NFR-27、NFR-31、NFR-32、NFR-33、NFR-36、NFR-37、NFR-38、NFR-40、NFR-41、NFR-42、NFR-47、NFR-49）と監査 4（NFR-16、NFR-28、NFR-48、NFR-50）。試験の環境の取引が乱しうる NFR-24、NFR-26 と SLI-12、EBP-01 |
| docs/quality/qr/ | 保守性と移植性の品質要求 QR-14、QR-33、QR-38、QR-39、QR-40、QR-50〜QR-56、QR-67、QR-69 |
| docs/quality/fr/ | 時刻、ID、外部のシステムに頼る受け入れ基準（FR-04、FR-12、FR-22、FR-23、FR-26、FR-29、FR-30、FR-39、FR-40、FR-46、FR-47、FR-51、FR-52、FR-53、FR-54 ほか）。偽物と差し替え口が届くべきもの |
| docs/quality/context.yaml | CON-03〜CON-06、EXT-01、EXT-02、OPF-01〜OPF-03 |
| docs/quality/qas/ | QAS-28（NFR-16 の頻度）。ほかのゲートのしきい値の QAS（QAS-35、QAS-37、QAS-39）は、出どころの決め方を変えない |
| 公開の情報: [Node.js のリリースの予定](https://nodejs.org/en/blog/announcements/evolving-the-nodejs-release-schedule)、[endoflife.date の Node.js](https://endoflife.date/nodejs)、[Node.js の TypeScript の文書](https://nodejs.org/api/typescript.html) | Node.js 26 が 2026 年 10 月に Active LTS になった。型を外して .ts を動かす仕組みは 24.12 と 25.2 から安定 |
| 公開の情報: [TypeScript 7.0 の発表](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/) | 7.0 は Go の tsc で、プログラムから使う API を持たず、それに頼る道具は 6.0 を使う |
| 公開の情報: [Oxlint の規則の一覧](https://oxc.rs/docs/guide/usage/linter/rules.html)、[Oxlint の設定](https://oxc.rs/docs/guide/usage/linter/config.html)、[Oxfmt のベータ](https://oxc.rs/blog/2026-02-24-oxfmt-beta) | Oxlint は no-restricted-imports（patterns、regex）、no-restricted-globals、no-restricted-properties、import/no-cycle、import/no-relative-parent-imports、react/jsx-no-literals、jsx-a11y の規則と、ファイルの場所ごとの overrides を持つ（import/no-restricted-paths と no-restricted-syntax はない）。Oxfmt はベータで、--check で違いを示す |
| 公開の情報: [Vitest 4 の発表](https://voidzero.dev/posts/announcing-vitest-4)、[React Router v8](https://remix.run/blog/react-router-v8) | Vitest 4 で Browser Mode が安定し、Playwright の提供者で WebKit を動かせる。React Router 8 は 2026 年 6 月に出て、データの組み立て方を持ち、React 19 を求める |
| 公開の情報: [Turso のローカルの開発](https://docs.turso.tech/local-development)、[Turso と Drizzle](https://docs.turso.tech/sdk/ts/orm/drizzle)、[@hono/zod-openapi の README](https://github.com/honojs/middleware/blob/main/packages/zod-openapi/README.md) | ローカルでは libSQL のデータベースのファイルか libSQL のサーバーを使い、Drizzle は @libsql/client でつなぐ。@hono/zod-openapi は経路の定義から OpenAPI 3.1 の文書を生成する |
| 公開の情報: [Stripe のサンドボックス](https://docs.stripe.com/sandboxes)、[サンドボックスの管理](https://docs.stripe.com/sandboxes/dashboard/manage)、[Stripe CLI の sandbox](https://docs.stripe.com/cli/sandbox) | サンドボックスは分かれたテストの環境で、アカウントごとに最大 5 まで作れ、そのデータと操作はほかのサンドボックスから分かれ、API の鍵はサンドボックスの中で管理する。自動のテストが設定やデータに触れないよう、ローカルの開発と CI には別のサンドボックスを使うよう勧める。CLI の例では、サンドボックスが自身のアカウントの ID を持つ |
| 公開の情報: [React Aria の品質](https://react-aria.adobe.com/quality) | React Aria は、試している支援技術に iOS の VoiceOver を挙げる（ブラウザと iOS の版は書いていない） |
| 公開の情報: [Trivy の脆弱性の調べ](https://trivy.dev/latest/docs/scanner/vulnerability/)、[Trivy のリポジトリ](https://github.com/aquasecurity/trivy) | Trivy は Apache-2.0 で、コンテナのイメージのもとの OS の部品と言語の部品の脆弱性を調べる。パッケージの管理の外の実行の部品は一部でしか見つけない |
| 公開の情報: [Node.js のリリースの一覧](https://nodejs.org/dist/index.json) | 版ごとに、セキュリティのリリースかを示す（security の項目） |
| 公開の情報: [Apple のベータ版の入れ方](https://developer.apple.com/support/install-beta/)、[Apple Beta Software Program](https://beta.apple.com/) | 公開の候補の版（RC）は、ふつう、主な版を利用者に出す前の最後のベータ版として出る。ベータ版は、Apple Developer のサイトに入る Apple Account か Apple Beta Software Program で端末に入れる |

既存のコードはなく、読んだコードもない。確かめていないのは、Drizzle ORM の 1 系が正式に出たか、TanStack Query、React Aria Components、pnpm、pino、openapi-typescript、openapi-fetch、oasdiff、secretlint、mkcert の今の版、Trivy が Node.js の実行の部品そのものの脆弱性を見つけるか（そのため Node.js の版はリリースの一覧で調べる）、ダッシュボードで作る Stripe のサンドボックスがそれぞれ別のアカウントの ID を持つこと（CLI の例でだけ読んだ。違えばリリースの手順のアカウントの確かめが試験の環境を立てず、気づける）と、ホーム画面に加えた ELM-01 の実機での振る舞い（DAS-03）。

## すでに決まっていたこと
| 出どころ | 決めていること | 従う方針 |
|---|---|---|
| TC-01、TC-02、TC-03 | 言語は TypeScript、画面は React、サーバーは Hono | POL-01 |
| TC-04、TC-05 | 静的な検査は Oxlint、整形は Oxfmt | POL-02、POL-04 |
| TC-06 | テストは Vitest | POL-03 |
| TC-07、TC-08 | 本番は Turso と Cloud Run として設計する（想定） | POL-01、POL-04 |
| TC-09 | 作る、試す、動かすことはローカルだけで完結させ、何も配備しない | POL-01、POL-02、POL-03、POL-04、POL-05（DEC-32） |
| TC-10、TC-11、TC-12 | 決済は Stripe のテスト環境、カードの情報は入力部品で通さない、地図は Google Maps Platform | POL-01、POL-03、POL-04、POL-05（DEC-34） |
| TC-13 | 乗客とドライバーは iOS の Safari の Web アプリ | POL-01、POL-03、POL-04 |
| TC-15 | 新しい版はデモの回を開くときに配備する | POL-04 |
| PC-03、TEAM-01 | 開発者 1 人が作り、動かし、保守する | POL-02、POL-03、POL-06 |
| DEC-01 | 一つの配車サーバー（中を機能ごとの部分に分ける）、二つの Web アプリ、一つのデータベース | POL-02（DEC-31。中の分け方は FND-11） |
| DEC-02、DEC-03、DEC-04 | ELM-01 は iOS 18.4 以降の Safari、ELM-02 はコンピューターの主なブラウザ、ELM-03 は Node.js の Active LTS をコンテナで。Web アプリの静的なファイルは ELM-03 が配る | POL-01（DEC-34） |
| DEC-05、DEC-18 | 想定の本番とローカルの置き方。ローカルの定期の呼び出しと HTTPS の証明書はこの段階に任せた | POL-01、POL-03、POL-04 |
| DEC-08、DEC-10 | 依頼の状態の条件つきの書き込みと冪等キー、お金の操作の試みごとのキーと結果が分からない状態 | POL-02、POL-03 の偽物 |
| DEC-09〜DEC-13、DEC-21 | 外部のシステムは ELM-03 のそれぞれのつなぎ口の後ろに置く | POL-02、POL-03、POL-05 |
| DEC-11 | EXT-01 の期間の取引と返金を日々読んで記録と突き合わせる | POL-03、POL-04（試験の環境とローカルの本番の外部のアカウントを分ける） |
| DEC-12 | カードの情報は入力部品から EXT-01 に直接渡し、登録の結果はサーバーが EXT-01 から読み直す | POL-03 の偽物、DEC-34 |
| DEC-15、DEC-24 | 隠す決まりと届ける相手の規則は一か所 | POL-02、POL-04 |
| DEC-16、DEC-17 | 記録した日ごとの鍵（読み方、作り方、捨て方はこの段階に任せた）、ELM-04 を書くのは ELM-03 だけ | POL-02、POL-04（DEC-29） |
| DEC-19、DEC-20 | たどる記録と標準出力のログ、異常の知らせと想定の本番の見張り | POL-03、POL-04、POL-05 |
| DEC-26 | 切り替え、足すだけのデータの形、前の版の配備し直し（配備と戻しの手順とデータの形を変える道具はこの段階に任せた） | POL-04（同じ選び方。FND-11） |
| DAS-03（確認済み） | ホーム画面に加えた Web アプリの振る舞いは、開発の中と NFR-15 の受け入れで実機で確かめる | POL-03 |
| 設計の第 1 段階の決めたこと 1 | 監査は想定の本番の要求として設計し、実際には行わない | POL-03 |

既存のコードはなく、従うコードの約束事もない。この段階に宛てた申し送りもない。

## 技術方針
<!-- generated: policies -->
| POL | 名前 | 範囲 | 対象 | 決定 | 根拠 |
|---|---|---|---|---|---|
| POL-01 | コンポーネントの種類ごとの技術の組み合わせと、どのコンポーネントも使う道具 | 技術の選定 | DRV-17、DRV-15、DRV-16、DRV-22 | DEC-02、DEC-03、DEC-04、DEC-05、DEC-17、DEC-28、DEC-29、DEC-30、DEC-33、DEC-34 | 仮定 |
| POL-02 | 一つのリポジトリをコンポーネントごとに分け、その中を業務の機能ごとに分け、境を Oxlint で守る | リポジトリとディレクトリ | DRV-12、DRV-33、DRV-35、DRV-34、DRV-31、DRV-16 | DEC-01、DEC-05、DEC-08、DEC-10、DEC-15、DEC-17、DEC-24、DEC-31、DEC-33、DEC-34 | 推定 |
| POL-03 | テストの層、偽物、環境と、品質チェーンのゲートの出どころと監査の置き場所 | テスト戦略とゲート | DRV-33、DRV-12、DRV-13、DRV-02、DRV-07、DRV-14、DRV-22、DRV-24、DRV-27、QR-14 | DEC-02、DEC-06、DEC-08、DEC-09、DEC-10、DEC-11、DEC-12、DEC-13、DEC-15、DEC-18、DEC-20、DEC-21、DEC-22、DEC-24、DEC-25、DEC-26、DEC-32、DEC-34 | 仮定 |
| POL-04 | パイプライン、配備と戻し、静的な検査と、コードの中の約束事 | CI/CD とコードの約束事 | DRV-13、DRV-12、DRV-15、DRV-16、DRV-24、DRV-29、DRV-34、DRV-18、DRV-07、DRV-27 | DEC-05、DEC-11、DEC-15、DEC-16、DEC-18、DEC-19、DEC-20、DEC-21、DEC-26、DEC-30、DEC-32、DEC-34 | 仮定 |
| POL-05 | インタフェースの種類ごとの仕様書の作り方 | 仕様書の作り方 | DRV-12、DRV-13、DRV-16、DRV-18 | DEC-06、DEC-11、DEC-12、DEC-13、DEC-20、DEC-21、DEC-29、DEC-33、DEC-34 | 推定 |
| POL-06 | コーディングエージェントが設計を見つける道と、実装からの指摘の戻り方 | 実装からの戻り | — | DEC-32 | 推定 |
<!-- /generated -->

POL-01、POL-03、POL-04 は、開発者についての仮定（DAS-07、DAS-08、DAS-09）か品質チェーンの未確認の仮定（QAS-28）を前提に持つため、根拠は仮定。POL-06 は設計を動かす要求には仕えず、設計の連鎖の実装からの指摘の決まりに仕える。

## 設計の決定
<!-- generated: decisions -->
| DEC | 名前 | 対象 | 根拠 |
|---|---|---|---|
| DEC-28 | 二つの Web アプリは Vite で単一ページのアプリとして作り、React Router、TanStack Query、React Aria Components を使う | DRV-16、DRV-22、DRV-15、DRV-12 | 仮定 |
| DEC-29 | ELM-04 の読み書きは Drizzle ORM で行い、データの形の変更は drizzle-kit が生成する SQL のマイグレーションで行う | DRV-16、DRV-15、DRV-13、DRV-02、DRV-07 | 仮定 |
| DEC-30 | 本人の確かめは認証のライブラリを使わず、Hono の仕組みと node:crypto で作る | DRV-28、DRV-16、DRV-15、DRV-19 | 推定 |
| DEC-31 | コードは一つのリポジトリでコンポーネントごとに分け、その中を業務の機能ごとに、機能の中を規則、流れ、つなぎ口に分け、境を Oxlint で守る | DRV-12、DRV-33、DRV-35、DRV-34、DRV-16 | 推定 |
| DEC-32 | パイプラインは開発者のマシンだけで動かし、変更のたびの検査は git のフックが、リリースの前の確かめは版の印から起こすリリースの手順が行う | DRV-15、DRV-16、DRV-12、DRV-13 | 仮定 |
| DEC-33 | ELM-03 の HTTP の仕様書は Zod の経路の定義から生成し、二つの Web アプリはそれから生成した型で ELM-03 を呼ぶ | DRV-12、DRV-13、DRV-16 | 仮定 |
| DEC-34 | Web アプリは環境ごとの値を起動のときに ELM-03 から読み、端から端の層のブラウザの側の偽物はその値で src/platform/ に差し込む | DRV-07、DRV-16、DRV-13、DRV-33、FND-12、FND-13 | 推定 |
<!-- /generated -->

どの決定も尋ねていない。言語、画面、サーバーの技術は TC-01〜TC-03 が決めており、選んだ主なライブラリはどれも自身の入口、表、エラーの形を持ち込まない（認証のライブラリは DEC-30 で使わず、@hono/zod-openapi の既定のエラーの形は POL-04 で替える）。どれも費用がかからず、影響の広さと重大さは高に届かない。DEC-34 は FND-12 と FND-13 を受けて加えた。一度だけ作ったものを試験の環境で確かめてそのまま配備することと、設定を環境から読むことは技術方針の決まりで、残る案の比べ方も下の表で決まるため、尋ねる点ではない（推定）。

DEC-28 二つの Web アプリの組み立て方（どの案も React 19 の上で、二つ目と三つ目も部品は React Aria Components とする）:

| 要求（順位） | Vite、React Router、TanStack Query、React Aria Components | React Router のフレームワークの組み立て方 | Next.js の静的な書き出し | React と Vite だけ |
|---|---|---|---|---|
| DRV-15（6） | 満たす | 満たす | 満たす | 満たす |
| DRV-16（7） | 満たす | 一部（使わないサーバーの機能の決まり） | 一部（Hono の ELM-03 と役割が重なる） | 一部（画面の行き来と部品を自分で作る） |
| DRV-12（12） | 満たす | 満たす | 満たす | 満たす |
| DRV-22（17、交渉できない） | 満たす | 満たす | 満たす | 一部（候補の一覧つきの入力を自分で作る） |

DEC-29 ELM-04 の読み書きとデータの形の変更:

| 要求（順位） | Drizzle ORM と drizzle-kit | Kysely | @libsql/client と自作の適用器 |
|---|---|---|---|
| DRV-07（4） | 満たす | 満たす | 満たす |
| DRV-15（6） | 満たす（一つのつなぎ方） | 満たす（方言の部品を足す） | 満たす |
| DRV-16（7） | 満たす | 一部（表の型を別に揃える） | 一部（型の対応と適用器を自作） |
| DRV-02（10） | 満たす | 満たす | 満たす |
| DRV-13（30） | 満たす（SQL のマイグレーション） | 満たす | 一部（適用と記録を自作） |

DEC-30 本人の確かめを作る部品:

| 要求（順位） | 認証のライブラリなし（Hono と node:crypto） | 認証のライブラリ |
|---|---|---|
| DRV-15（6） | 満たす | 満たす |
| DRV-16（7） | 満たす（要る分だけ作る） | 一部（使わない機能と拡張） |
| DRV-28（8） | 満たす（NFR-27 のテストで守る） | 満たす |
| DRV-19（26） | 満たす | 一部（設定の符号の流れを拡張で作る） |

二つ目を退けた決め手は、ライブラリ自身の入口、表、エラーの形が、第 3 段階の決めるインタフェースとデータの実体を縛ること。

DEC-31 コードの分け方:

| 要求（順位） | 業務の機能ごと、規則と流れとつなぎ口、Oxlint | 技術の層ごと | 機能ごとのパッケージ |
|---|---|---|---|
| DRV-16（7） | 満たす | 満たす | 一部（パッケージごとの設定と組み立て） |
| DRV-12（12） | 満たす（検査で境を守る） | 満たさない（境を検査できない） | 満たす |
| DRV-33（原則） | 満たす（ポートに偽物） | 一部 | 満たす |
| DRV-34、DRV-35（原則） | 満たす（一つの機能のディレクトリ） | 一部（層に散る） | 満たす |

DEC-32 パイプラインを動かす所:

| 要求（順位） | 開発者のマシンのフックとリリースの手順 | 開発者のマシンの CI のサーバー | 外部の CI のサービス |
|---|---|---|---|
| DRV-15（6、交渉できない） | 満たす | 満たす | 外した（TC-09 を破る） |
| DRV-16（7） | 満たす | 一部（CI のサーバーを保つ） | — |
| DRV-12（12） | 満たす（フックと、リリースの手順のやり直し） | 満たす | — |
| DRV-13（30） | 満たす（試験の環境で予行） | 満たす | — |

DEC-33 HTTP の仕様書と Web アプリの型:

| 要求（順位） | 生成した OpenAPI と生成した型 | Hono の RPC | 手で書く OpenAPI |
|---|---|---|---|
| DRV-16（7） | 満たす | 満たす | 一部（写しを手で保つ） |
| DRV-12（12） | 満たす（コンポーネントの間で import しない） | 一部（Web アプリがサーバーのコードの型を import する） | 満たす |
| DRV-13（30） | 満たす（前のリリースの文書と比べる） | 一部（比べる文書がない） | 満たす |

DEC-34 Web アプリが環境ごとの値を受け取る道:

| 要求（順位） | 起動のときに ELM-03 から読み、偽物は src/platform/ に | 環境ごとにビルドする | ビルドは一つで、偽物は通信の層 |
|---|---|---|---|
| DRV-07（4） | 満たす（環境ごとの外部のアカウント） | 満たす | 満たさない（同じサンドボックスを使う、FND-13） |
| DRV-15（6、交渉できない） | 満たす | 満たす | 満たす |
| DRV-16（7） | 満たす | 一部（三つのビルドとイメージ） | 一部（Stripe.js と地図の部品を真似る偽物） |
| DRV-13（30） | 満たす（確かめたイメージを配備） | 満たさない（確かめていないビルドを配備） | 満たす |
| DRV-33（原則） | 満たす（Web アプリのポート） | 満たす | 一部（通信の層だけ） |

## リポジトリとディレクトリ
ride-hailing-app-demo（今のリポジトリ）一つに、三つのコンポーネントを置く。コンポーネントはどれも TEAM-01 が持つため、木にはチームを書かない。ELM-03 の機能のディレクトリの名前は、第 2 段階の決定から取った例で、第 4 段階の ELM-03 のモジュールが決まったらそれに沿う。

```
ride-hailing-app-demo/
├── apps/
│   ├── server/              ELM-03 配車サーバー
│   │   ├── src/
│   │   │   ├── 機能/        業務の機能ごと（下の例）。domain/、application/、adapters/、index.ts
│   │   │   ├── platform/    時計、ID と乱数、設定、秘密の値と鍵、暗号、ログ。db/ はデータベースのつなぎ
│   │   │   └── http/        Hono のアプリの組み立て、境界のエラーの変換、仕様書の生成
│   │   ├── migrations/      drizzle-kit が生成した SQL（コミットする）
│   │   ├── generated/       openapi.json（コミットする）
│   │   └── test/            結合と契約の層
│   ├── rider/               ELM-01 乗客とドライバーの Web アプリ
│   │   └── src/             画面の機能ごとのディレクトリと platform/（呼び出しと流れ、ELM-03 から読む値、位置、画面を消さない仕組み、Web Push、EXT-01 の入力部品と地図の包み、それらの偽物、文言と書式）
│   └── console/             ELM-02 担当者とエンジニアの Web アプリ
│       └── src/             画面の機能ごとのディレクトリと platform/
├── packages/
│   ├── api-client/          ELM-03 の仕様書から生成した型と呼び出し（ELM-01、ELM-02 が使う）
│   └── config/              TypeScript、Oxlint、Oxfmt の共有の設定
├── tests/                   端から端と運用の予行の層
├── infra/
│   ├── local/               試験の環境とローカルの本番の Compose（秘密の値でない環境ごとの設定）、ローカルの定期の呼び出し
│   └── gcp/                 想定の本番の定義（どこにも当てない、TC-09）
├── scripts/                 パイプラインの手順と git のフック
├── docs/                    design/、quality/、releases/（リリースの記録）、records/（運賃表の照合の記録）
├── CLAUDE.md                コーディングエージェントへの指示書（POL-06）
└── .claude/skills/          設計のスキル
```

秘密の値は、リポジトリの外に環境ごとに分けたディレクトリ（試験用と、ローカルの本番のもの）に置く（POL-04）。

ELM-03 の機能のディレクトリの例: rides（依頼と乗車、確認コード、DEC-08、DEC-25）、dispatch（届ける相手の規則と評価のまとめ方、DEC-24）、payments（お金の操作と照合、DEC-09〜DEC-11）、places（場所、見積もり、料金、DEC-13）、locations（現在地と走っているかの判断、DEC-07、DEC-22）、accounts（アカウントと本人の確かめ、DEC-14、DEC-30）、access（使える機能、見せる範囲、隠す決まり、DEC-15）、operations（苦情、返金、登録、停止）、messages（連絡、DEC-27）、notifications（流れと Web Push、DEC-06、DEC-21）、tracing（たどる記録、操作の記録、異常、SLI の出来事、DEC-19、DEC-20、DEC-23）、jobs（期限の処理と日々の処理、DEC-18）、switches（振る舞いの切り替え、DEC-26）。

コンポーネントの間で許す依存:

```mermaid
flowchart LR
  rider["apps/rider - ELM-01"] --> client["packages/api-client"]
  console["apps/console - ELM-02"] --> client
  client -. "ELM-03 の仕様書から生成" .-> server["apps/server - ELM-03"]
  rider --> cfg["packages/config"]
  console --> cfg
  server --> cfg
```

一つの機能の中と、機能の間で許す依存（ELM-03）:

```mermaid
flowchart TB
  http["src/http/ - Hono のアプリと境界のエラーの変換"] --> ad
  subgraph cap["src/機能/"]
    ad["adapters/ - 経路、表、外部のつなぎ口"] --> app["application/ - 操作の流れとポート"]
    app --> dom["domain/ - 業務の規則"]
    ad --> dom
    idx["index.ts"]
  end
  other["src/別の機能/"] -->|"index.ts からだけ"| idx
  ad --> plat["src/platform/ - 時計、ID、設定、鍵、暗号、ログ"]
  app --> plat
  ad --> pdb["src/platform/db/ - データベースのつなぎ"]
  ad -->|"payments、places、notifications だけ"| ext["外部のシステムの部品と、外へ HTTP を呼ぶ fetch"]
```

apps/ のコンポーネントは互いに import せず、ELM-01 と ELM-02 は ELM-03 を packages/api-client からだけ呼ぶ。コンポーネントの中では、機能は別の機能を index.ts からだけ使い、domain/ はフレームワーク、データベース、外部の部品、adapters/、application/、src/platform/ を使わず、application/ は adapters/、データベースの部品、src/platform/db/ を使わない。外部のシステムの部品と、外へ HTTP を呼ぶ大域の fetch、node:http と node:https の呼び出しは、外部のシステムを持つ機能（payments、places、notifications）の adapters/ だけが使い、時刻、乱数、ID のもとと node:crypto は src/platform/ だけが使う。ELM-01 と ELM-02 では、EXT-01 の入力部品と地図を描く部品、ブラウザの位置などの仕組みと大域の fetch は src/platform/ だけが使い、POL-03 の偽物はそこに差し込む。どれも Oxlint の規則で、検査の手順が守る（POL-02）。表を書くのはその表を持つ機能の adapters/ だけで、表の定義を index.ts から出さないことは import の規則が守り、SQL の文でほかの機能の表を書くことだけは開発者のレビューが見る。変更のシナリオ DRV-12 の一つの機能の変更は、ELM-03 の一つの機能のディレクトリと、それを示す ELM-01 か ELM-02 の画面の機能のディレクトリに触れ、ELM-03 の HTTP の操作が変われば仕様書と api-client を生成し直す。触れるチームは TEAM-01 だけ。

## パイプライン
```mermaid
flowchart LR
  change(["main への commit か merge"]) --> check["check - 秘密の値を受けない"]
  check -- "失敗すると main に入れない" --> main(["main"])
  main -- "版の印と pnpm release" --> release["release"]
  release --> redo["check のやり直しと DoD の行の確かめ"]
  redo --> image["イメージを一度だけ作り、deps-audit で調べる"]
  image --> fake["試験の環境（偽物の設定）- 端から端と運用の予行"]
  fake --> acct["試験の環境とローカルの本番が別の外部のアカウントを名指すかの確かめ"]
  acct --> real["試験の環境（本物の外部サービスの設定、試験用のアカウント）- 契約と NFR-47"]
  real --> device["device-acceptance - 実機の受け入れ"]
  device --> pre["配備の前の一度だけの処理 - EXT-01 のアカウントの確かめとマイグレーション"]
  pre -- "どれかが通らなければ配備しない" --> local(["ローカルの本番 ELM-10 - 自身の外部のアカウント"])
  local -. "想定の本番。実際には動かさない" .-> cloud(["Cloud Run と Turso - open-session と close-session"])
  ios(["iOS と Safari の更新のベータ版か公開の候補の版。なければ公開された版"]) --> device2["device-acceptance - 通らなければ公開までに直す"]
  back(["戻すと決める"]) --> rollback["rollback"]
  week(["週に一度、想定の運用"]) --> audit["deps-audit - 何も止めない"]
```

どの手順も開発者のマシンで動く（DEC-32）。フックは pnpm install が入れ、main への merge は早送りしないため、main に入るどの変更でも check が動く。check はフックを飛ばすと止まらないが、release がフックの設定と DoD の行を確かめ、check を初めからやり直すため、通らない変更は配備されない。check は秘密の値も外部のアカウントも受けず、release と device-acceptance は試験用のディレクトリのものだけを受け、ローカルの本番のディレクトリはローカルの本番のコンテナに渡すだけで手順は読まない。ローカルの本番に配備する前の一度だけの処理は、そのコンテナの中で、鍵で届く EXT-01 のアカウントが設定の名指すものであることを確かめる。手順の中身と、手順ごとに受ける秘密の値は POL-04 にある。

## ゲートの出どころ
<!-- generated: gate-bindings -->
| NFR | 名前 | 確かめる所 | 出どころの方針 | 代わりの要求 |
|---|---|---|---|---|
| NFR-09 | 到着予定時刻と料金の決まりを地図のサービスを使わずに試すゲート | CI | POL-03 | — |
| NFR-11 | 通信の途切れと操作の重なりを再現する試験のゲート | リリース前の確認 | POL-03 | — |
| NFR-13 | 同じ名前の場所の取り違えを防ぐ受け入れの試験 | リリース前の確認 | POL-03 | — |
| NFR-15 | スマートフォンとブラウザの更新に合わせた試験のゲート | リリース前の確認 | POL-03 | — |
| NFR-21 | 乗車を始める判断と走っている間の判断を試すゲート | CI | POL-03 | — |
| NFR-22 | 登録の訂正を乗客に示す手がかりに反映する受け入れの試験 | リリース前の確認 | POL-03 | — |
| NFR-25 | 料金と返金の決まりを決済サービスを使わずに試すゲート | CI | POL-03 | — |
| NFR-27 | 本人の確かめと見られる範囲を試すゲート | CI | POL-03 | — |
| NFR-31 | ドライバーに示す場所と乗客が決めた場所の一致の受け入れの試験 | リリース前の確認 | POL-03 | — |
| NFR-32 | 操作を誰がいつ行ったかを残す完成の定義 | 完成の定義 | POL-03 | — |
| NFR-33 | 少ない操作で評価を送れることの受け入れの試験 | リリース前の確認 | POL-03 | — |
| NFR-36 | 依頼を届ける相手を決める規則を試すゲート | CI | POL-03 | — |
| NFR-37 | 状態の変化、端末のエラー、苦情を記録する完成の定義 | 完成の定義 | POL-03 | — |
| NFR-38 | 異常の知らせとたどりを確かめるリリース前の確認 | リリース前の確認 | POL-03 | — |
| NFR-40 | 変えなかった機能を公開の前に確かめる自動の試験のゲート | CI | POL-03 | — |
| NFR-41 | 自動の配備と前の版への戻しを確かめるリリース前の確認 | リリース前の確認 | POL-03 | — |
| NFR-42 | データを移す予行のリリース前の確認 | リリース前の確認 | POL-03 | — |
| NFR-47 | カードの情報がシステムを通らないことを確かめるリリース前の確認 | リリース前の確認 | POL-03 | — |
| NFR-49 | 画面のアクセシビリティの自動の検査 | CI | POL-03 | — |
<!-- /generated -->

品質チェーンのゲート 19 はすべて POL-03 が出どころを決め、代わりの要求はない。CI のゲート 7（NFR-09、NFR-21、NFR-25、NFR-27、NFR-36、NFR-40、NFR-49）は検査の手順（check）で、リリース前の確認のゲート 10（NFR-11、NFR-13、NFR-15、NFR-22、NFR-31、NFR-33、NFR-38、NFR-41、NFR-42、NFR-47）はリリースの手順（release）で、完成の定義のゲート 2（NFR-32、NFR-37）は main に入れる commit の DoD の行と、それを読む検査の手順で確かめる。CI は TC-09 のとおり開発者のマシンの git のフックで動く。開発者 1 人の体制で DoD の行に印を付ける二人目はいないため、検査の手順がその行を読み、当てはまる変更に印がなければ main に入れない。人が行うゲートの確かめは NFR-15 の実機の受け入れだけで、開発者が行う（DAS-09）。NFR-15 は、対応する iOS と Safari の更新を、Apple が公開の前に出すベータ版か公開の候補の版でも確かめ、前もって出る版のない更新は、通るまで参加者に更新を待ってもらう案内（範囲外）で、NFR-15 のしきい値を保つ。NFR-47 は、ローカルの本番と別の試験用の Stripe のサンドボックスで確かめる。品質チェーンのほかの非機能要件は、SLO（第 3 段階が SLI を結び付ける）と監視。

## 監査の置き場所
<!-- generated: audit-bindings -->
| NFR | 名前 | 置き場所の方針 | 代わりの要求 |
|---|---|---|---|
| NFR-16 | 止まってから再開する回復の訓練 | POL-03 | — |
| NFR-28 | 脆弱性の修正期限と侵入試験 | POL-03 | — |
| NFR-48 | 模擬の運賃表と模す運賃の定めの照合 | POL-03 | — |
| NFR-50 | 画面のアクセシビリティの人による確かめ | POL-03 | — |
<!-- /generated -->

監査 4 はすべて POL-03 が置き場所を決め、代わりの要求はない。設計の第 1 段階の決めたこと 1 のとおり、何も配備しない間は実際には行わず、パイプラインの手順で動く支えの道具（運用の予行の層、依存の部品とイメージの脆弱性の調べ、axe-core）だけが実際に動く。NFR-28 の期限を保つ記録は、依存の部品（pnpm audit）、リリースのイメージのもとの OS の部品（Trivy）、イメージの Node.js の版（Node.js のリリースの一覧）のどれに見つけた脆弱性にも開く。誰が行うかは入力になく、DAS-09 で開発者とした。NFR-28 の記録は脆弱性と個人の情報を含みうるため、リポジトリの外に置く。NFR-48 は、模す運賃の定めの中身と照らす役割を品質チェーンがまだ決めておらず（品質チェーンの未解決の点）、置き場所はあっても照らすものがない。

## インタフェースの種類
| インタフェースの種類 | 現れる所 | 仕様書の決め方 |
|---|---|---|
| ELM-01、ELM-02 から ELM-03 への HTTPS の要求と応答（起動のときに読む環境ごとの値の操作、DEC-34 を含む） | 実行時の構成の ELM-01、ELM-02 → ELM-03 | POL-05 の一つ目（コードから生成する） |
| ELM-03 から ELM-01、ELM-02 への流れ（Server-Sent Events） | 実行時の構成の ELM-03 → ELM-01、ELM-02 | POL-05 の一つ目（コードから生成する） |
| 日々の呼び出し（想定の本番の Cloud Scheduler、ローカルの定期の呼び出し）と外からの生存確認から ELM-03 へ | 実行時の構成の定期の呼び出し、配置のビュー、脅威のモデルの F12 と F13 | POL-05 の一つ目（コードから生成する） |
| ELM-03 から ELM-04 への取引 | 実行時の構成の ELM-03 → ELM-04 | POL-05 の二つ目（コードから生成する） |
| ELM-03 から ELM-05 の API と、ELM-01 の中の ELM-05 の入力部品 | 外部との関係と実行時の構成の ELM-03 → ELM-05、ELM-01 → ELM-05 | POL-05 の三つ目（相手の文書） |
| ELM-03 から ELM-06 の API と、ELM-01 が地図を描くもの | 外部との関係と実行時の構成の ELM-03 → ELM-06、ELM-01 → ELM-06 | POL-05 の四つ目（相手の文書） |
| ELM-03 から ELM-07 を経て ELM-01、ELM-02 への Web Push | 外部との関係と実行時の構成の ELM-03 → ELM-07 → ELM-01、ELM-02 | POL-05 の五つ目（相手の文書） |
| ELM-03 から想定の本番のログへの、日々の処理を終えた記録 | 配置のビューと脅威のモデル（DEC-20） | POL-05 の六つ目（作らない） |
| 乗客、ドライバー、担当者、エンジニアの画面 | 外部との関係の USR-01〜USR-04 | POL-05 の七つ目（作らない） |

ほかの者がこのシステムの決めた決まりに合わせて作るインタフェースは今はなく、POL-05 の八つ目（手で書く）はどれにも当たらない。想定の本番のアラートから開発者へのメール（F14）はプラットフォームが送るもので、このシステムのコードのインタフェースではない。Web アプリが起動のときに読む環境ごとの値を渡す操作は一つ目の種類に入り、その中身は HND-15 で第 3 段階が決める。

## 指摘
<!-- generated: findings -->
| FND | 名前 | 重さ | 出した段 | 宛先 | 状態 | 変えた項目 |
|---|---|---|---|---|---|---|
| FND-11 | DEC-01 と DEC-26 が、第 2b 段階が確定の深さで決めるコードの分け方とリリースの戻し方を決めている | 軽微 | architecture-to-technical-policy | architecture-drivers-to-architecture | 未解決 | DEC-31、POL-04 |
| FND-12 | Web アプリがビルドのときの値だけを読み、そのビルドを一度だけ作るため、試験の環境の偽物の設定で ELM-01 の地図と EXT-01 の入力部品を替えられない | 中 | design-review | architecture-to-technical-policy | 受け入れ | DEC-34、HND-15、POL-01、POL-03、POL-04、POL-05 |
| FND-13 | 試験の環境の本物の外部サービスの設定がローカルの本番と同じ EXT-01 のテスト環境を使い、リリースのたびの取引が日々の照合と SLI-12 を乱す | 中 | design-review | architecture-to-technical-policy | 受け入れ | DEC-34、POL-01、POL-03、POL-04 |
| FND-14 | 依存の規則が、外部のシステムとデータベースのつなぎ口と ELM-01 の差し替え口を迂回する道を残している | 軽微 | design-review | architecture-to-technical-policy | 受け入れ | HND-14、POL-02 |
| FND-15 | NFR-15 の出どころは、iOS と Safari の更新が公開された後に確かめて直し始めるだけで、利用者が更新する前に直すことを保たない | 軽微 | design-review | architecture-to-technical-policy | 受け入れ | POL-03、POL-04 |
| FND-16 | EXT-01 の偽物が、支払い方法の登録の取引とその結果の読み直しを起こせない | 軽微 | design-review | architecture-to-technical-policy | 受け入れ | POL-03 |
| FND-17 | NFR-28 の修正の期限を保つ記録が、依存の部品の脆弱性にしか開かれない | 軽微 | design-review | architecture-to-technical-policy | 受け入れ | POL-03、POL-04 |
| FND-18 | DEC-28 の想定の一つに仮定がなく、POL-02、POL-03、POL-05、DEC-28 が頼る設計の与件と共有する事実を前提に挙げていない | 軽微 | design-review | architecture-to-technical-policy | 受け入れ | DEC-28、POL-02、POL-03、POL-05 |
<!-- /generated -->

この段階に宛てた指摘は、第 2b 段階の全体のレビュー（c14d073）が出した FND-12〜FND-18（中 2、軽微 5）で、どれも受け入れた。中の FND-12 は、Web アプリがビルドのときの値だけを読むことと、一度だけ作るイメージを試験の環境の二つの設定とローカルの本番で動かすことの食い違いで、DEC-34 で環境ごとの値を起動のときに ELM-03 から読むことにし、偽物を選べるのを開発と試験の環境の名前の設定だけにして閉じた。中の FND-13 は、試験の環境とローカルの本番が同じ EXT-01 のサンドボックスを使い、リリースのたびの取引が日々の照合（DEC-11）と主な設計を動かす要求 DRV-07 の測定量（NFR-26 の SLI-12、NFR-24）を乱すことと、試験だけの写しの守りがないことで、POL-04 で秘密の値と外部のアカウントを環境ごとに分け、手順ごとに受けるものを決め、別のアカウントであることを手順とテストで確かめ、試験だけのものをローカルの本番の設定で選べなくして閉じた。軽微の FND-14〜FND-18（依存の規則の抜け道、NFR-15 の公開の前の確かめ、EXT-01 の偽物の登録、イメージの脆弱性の調べ、前提の欠け）も、この実行で併せて扱った。受け入れて変えた項目は各指摘の resolution にある。FND-11（軽微、未解決）はこの段階が第 2 段階に出したもので、第 2 段階が次に走るときに扱い、それだけでは第 2 段階を走らせない。第 2 段階に宛てた FND-10 は、この段階の項目に触れない。

## 申し送り
<!-- generated: handoffs -->
| HND | 名前 | 書いた段 | 宛先 | コンポーネント | 状態 | 決めた項目 |
|---|---|---|---|---|---|---|
| HND-14 | EXT-01 を呼ぶクライアントの部品と、そのやり直しと時間切れの設定 | architecture-to-technical-policy | high-level-design-to-detailed-design | ELM-03 | 未決定 | FND-14 |
| HND-15 | Web アプリが起動のときに読む環境ごとの値を、ELM-03 が渡す操作 | architecture-to-technical-policy | architecture-to-high-level-design | — | 未決定 | — |
<!-- /generated -->

この段階に宛てた申し送りはない。この段階が書いたのは HND-14 と HND-15。HND-14 は、EXT-01 を呼ぶクライアントの部品と、その自動のやり直しと時間切れの設定を、お金を動かすモジュールを確定の深さで設計する第 4 段階の ELM-03 の実行に送るもので、その守る枠の POL-02 を、HTTP を直接呼ぶ案でも外への呼び出しを payments の機能の adapters/ に限るよう直した（FND-14）。表で HND-14 の「決めた項目」に FND-14 が出るのは、その指摘の basis_note が HND-14 を引くためで、HND-14 は未決定のまま。HND-15 は、Web アプリが起動のときに読む環境ごとの値を ELM-03 が渡す操作を、第 3 段階の次の実行に送る（DEC-34、FND-12）。どの機能の受け入れ基準も通らない操作のため、インタフェースを機能から組み立てる第 3 段階が取り上げないおそれがある。主なライブラリのほかの部品（Web Push、EXT-02 を呼ぶ部品、Stripe.js と地図を描く部品の包み方など）、ライブラリと道具の版、道具の設定、パイプラインのファイル、テストとテストデータは、実装が方針の中で決めるため、申し送りを書いていない。記録した日ごとの鍵をいつ作りいつ捨てるか（POL-04）と、各機能のポートの中身は、第 4 段階が ELM-03 のモジュールとして設計する。

## 決めたこと
| # | 質問 | 回答 | 項目 |
|---|---|---|---|

この段階は質問をしていない。尋ねる基準（影響の広さか重大さが高、入力の食い違い、入力が名指して中身を与えない決まり、影響が高の品質チェーンへの要求）に当たる点がなかった。言語、画面、サーバーの技術は TC-01〜TC-03 が決め、選んだ主なライブラリは自身の入口、表、エラーの形を持ち込まず、リポジトリは一つのチームのもので、費用のかかる道具も環境もなく（この実行で加えた試験用の Stripe のサンドボックス、Trivy、Apple のベータ版も無償）、品質チェーンへの要求もない。DEC-34 は、技術方針の決まり（一度だけ作ったものを環境から環境へ移す、設定を環境から読む）と入力から決まる選び方で、尋ねる点ではない。

## 未確認の仮定
<!-- generated: assumptions -->
| ID | 名前 | 種類 | 影響の広さ | 重大さ | 依存する項目 |
|---|---|---|---|---|---|
| DAS-09 | 人が行うゲートの確かめと監査は開発者が行う | 判断 | 低 | 低 | POL-03 |
| QAS-28 | 回復の訓練の頻度 | 暫定の決定 | 低 | 低 | POL-03 |
| DAS-07 | 開発者は技術方針の主なライブラリを使いこなすか、学ぶ時間を取れる | 判断 | 中 | 低 | DEC-28、DEC-29、DEC-33、POL-01 |
| DAS-08 | 開発者のマシンは macOS でコンテナを動かせ、iOS 18.4 以降の iPhone を一台テストに使え、それに iOS のベータ版を入れられる | 判断 | 中 | 低 | DEC-32、POL-01、POL-03、POL-04 |
<!-- /generated -->

QAS-28 の影響の広さと重大さは、この段階が評価し直した値（POL-03 の NFR-16 の置き場所だけが依存し、頻度が変わっても置く手順を替えるだけ）。DAS-08 は、テストに使う iPhone に iOS の更新のベータ版か公開の候補の版を入れられることと、開発者のマシンに Trivy を入れられることを加え（FND-15、FND-17）、評価は中、低のまま（ベータ版を入れられなくても、通るまで参加者に更新を待ってもらう案内で NFR-15 のしきい値を保て、出どころの起こるときが変わるだけ）。DAS-01（第 1 段階）は主なライブラリの選び方が直接は依存せず、それを受ける DAS-07 をこの段階が書いた。第 2 段階の DAS-02、DAS-04、DAS-05、DAS-06 には、この段階の項目は直接は依存せず、それを前提に持つ決定（DEC-03、DEC-05、DEC-09、DEC-20）に従うだけ。どの仮定にも答えは要らない。訂正があれば、回答と同じように次の実行で反映する。

## 未定の値
新しい未定の値はない。ゲートの出どころは、ゲートのしきい値（T_alert_delay、T_rollback、N_rating_operations、V_moving_lock など）を NFR に残し、方針に写していない。

## 未解決の点
- NFR-48 の照合は、模す運賃の定めの中身と照らす役割が品質チェーンで決まっていない（品質チェーンの未解決の点）。POL-03 は置き場所を決めたが、定めがなければ照らせない。
- ホーム画面に加えた ELM-01 の実機での振る舞い（DAS-03）は、コードができてから開発の中と NFR-15 の実機の受け入れで確かめる。この段階は確かめていない。

## 範囲外
- 開発者のマシンの用意（コンテナの実行環境、Node.js、Python 3、mkcert の認証局、Trivy）、テストに使う iPhone に mkcert の認証局を入れて信頼すること、試験用とローカルの本番の Stripe のサンドボックスと鍵と Web Push の鍵を作って環境ごとのディレクトリに置くこと: 開発者の作業。参加者の iPhone に認証局を入れることは、第 2 段階の範囲外の参加者への案内に加わる。
- iOS と Safari の更新のベータ版、公開の候補の版、公開された版が出たことに気づくこと: 開発者の運用。POL-04 の device-acceptance は、気づいた後に行う手順を決める。
- 前もって出る版のない iOS と Safari の更新で、実機の受け入れが通るまで参加者に更新を待ってもらう案内: 運用の決まり。そのような更新で NFR-15 のしきい値を保てるのは、この案内だけ。
- 監査の結果を受けて直すことを決め、閉じる手順と、誰が認めるか: 運用の決まり。POL-03 は置き場所と支える道具だけを決める。

## 次
この実行は中の指摘 FND-12 と FND-13 を受け入れて項目（POL-01、POL-03、POL-04、POL-05、DEC-34、HND-15）を変えたため、別の文脈で `design-review` をこの段階に実行する（c14d073 のレビューからの差分のレビュー）。レビューがこの段階に重大か中の指摘を出したら、この段階を再実行する（軽微な指摘のためには走らせない）。そのあと `architecture-to-high-level-design` を実行する。第 3 段階は、HND-15 で Web アプリが起動のときに読む値を渡す操作を ELM-03 の HTTP のインタフェースに入れ、各インタフェースの仕様書の作り方を POL-05 から、インタフェースが見せる約束事をコードがどう作るかを POL-04 から取る。第 4 段階（ELM-01、ELM-02、ELM-03）と実装は、変えた POL-01〜POL-05 と HND-14 に従う（どれもまだ走っていない）。この段階が第 2 段階に出した FND-11 は軽微で、第 2 段階を走らせる理由にはならない。品質チェーンへの要求は出しておらず、答えたものも反映を見つけたものもない。`docs/design/quality-chain-requests.md` は、QCR-01（未回答）と QCR-02〜QCR-05（回答済み）を挙げる。

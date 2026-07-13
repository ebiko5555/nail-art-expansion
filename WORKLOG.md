# 作業ログ

## 2026-07-13 13:25 — 調査と保護

- **Action**: 既存アプリ、Git状態、3Dモデル、Blender環境を調査。作業ブランチを作成し、未コミットの `index.html` と `hand.glb` を複製保存。
- **Files affected**: `.backups/2026-07-13-before-rigging/`
- **Notes**: Vault側の既存未コミット変更には触れていない。元モデル `hand.glb` は上書きしない。

## 2026-07-13 13:33 — モデル解析

- **Action**: Blender 4.5.9 LTSで候補モデルを読み取り専用解析し、対象 `hand.glb` の前面・背面・側面をレンダー。
- **Files affected**: `reports/inventory/`、`reports/model_views/`
- **Notes**: 対象は右手、指を開いた姿勢、単一メッシュ、4,416頂点、7,600ポリゴン、2材質、UVあり、アーマチュアとウェイトなし。プロジェクト内に配布リグ付きモデルは見つからなかった。

## 2026-07-13 13:38 — 初回リグ生成と自動補正

- **Action**: 17ボーン、近接距離ウェイト、9ポーズを自動生成。画像確認で爪が伸びる問題を検出し、爪の連結成分を各指の先端骨へ固定する補正を追加。
- **Files affected**: `rigging/build_rig.py`、`dist/`
- **Notes**: 皮膚部分の曲がりと頂点の有限値は初回テストで確認済み。補正版を再生成して再検証する。

## 2026-07-13 13:45 — Web組み込みとブラウザ検証

- **Action**: 17骨のクォータニオン追随、Rest Pose差分、平滑化、回転制限、5表示モード、鏡像、位置・大きさ・奥行き・透明度・曲がり調整を追加。
- **Files affected**: `index.html`、`rigged_hand.glb`
- **Notes**: デモモード、GLB読込、全骨取得、390×844縦画面、844×390横画面、表示切替を実ブラウザで確認。横はみ出しなし、コンソールerror／warning 0件。

## 2026-07-13 14:08 — 自然形状の配布モデルへ差し替え

- **Action**: SketchfabからCC BY-NC 4.0のリグ付き手を正規取得。元GLBを保持し、補助オブジェクトと埋込アニメーションをWeb用から除外、骨名をMediaPipe向けに統一した。
- **Files affected**: `assets/source_models/`、`rigging/prepare_anatomical_hand.py`、`dist/`、`rigged_hand.glb`
- **Notes**: 5,248頂点・4,370ポリゴン・22骨。作者表記と非商用条件をUI、README、第三者ライセンス表記へ追加。

## 2026-07-13 14:16 — 差し替え後の検証

- **Action**: 9ポーズの変形検査、GLB数値検査、縦390×844・横844×390のデモ表示、骨表示を確認。
- **Files affected**: `dist/pose_tests/`、`dist/rigging_validation.json`、`index.html`、`tests/static.test.mjs`、`tools/`
- **Notes**: 全ポーズで有限値、5,248頂点・4,370ポリゴンを維持。現在のローカルページではコンソールerror／warning 0件。

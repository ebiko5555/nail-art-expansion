# Nail Editor — Art Expansion 手トラッキング版

MediaPipe Handsの21ランドマークに、Blenderで自動リグ付けした水晶の手モデルを重ねるスマートフォン向け技術検証アプリです。

## スマートフォンで使う

1. [公開ページ](https://ebiko5555.github.io/nail-art-expansion/)をSafariまたはChromeで開く。
2. 「はじめる」を押し、カメラを許可する。
3. 手のひら全体が画面に入るようにかざす。
4. 必要なら「カメラ切替」と「鏡像表示」を調整する。

カメラを使わず確認する場合は「カメラなしでデモを見る」を選びます。

## 表示モード

- カメラ映像のみ
- カメラ＋3D手モデル
- 3D手モデルのみ
- MediaPipeランドマーク
- 骨表示デバッグ

「位置・追従の微調整」では、大きさ、透明度、左右・上下・奥行き、平滑化、指の曲がりを変更できます。

## Macでローカル確認

ターミナルでこのフォルダへ移動し、次を実行します。

```bash
python3 -m http.server 8788
```

ブラウザで `http://localhost:8788/` を開きます。通常ファイルのダブルクリックでは、カメラやGLB読込が正しく動かない場合があります。

## Blenderで確認

- `dist/rigged_hand.blend`: Rest Poseのリグ付きモデル
- `dist/rigged_hand_test.blend`: 9ポーズのテストアクション付き
- `dist/pose_tests/`: 自動ポーズの確認画像

Blender 4.5.9 LTSで生成・検証しています。

## GitHub Pages

このリポジトリは静的HTML構成です。`main`ブランチのルートをGitHub Pagesの公開元に設定すれば、追加ビルドなしで配信できます。`index.html`と`rigged_hand.glb`は同じ階層に置いてください。

## 自動テスト

```bash
node tests/static.test.mjs
python3 tools/verify_glb.py rigged_hand.glb
```

詳細は `rigging_report.md`、`export_report.md`、`LIMITATIONS.md`を参照してください。

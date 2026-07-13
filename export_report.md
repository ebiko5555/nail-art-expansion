# GLB書き出し・検証レポート

## 出力条件

- Blender 5.1.1（生成スクリプトは4.5以降を要求）
- GLB 2.0、単一メッシュ、Skinあり、22 Joints
- 必須17骨に加えて中手骨5本を保持
- 材質1、UV保持、外部テクスチャなし
- カメラ、ライト、原本バックアップはGLBへ含めない
- Rest Poseを書き出し、テストアニメーションはWeb用GLBから除外
- glTF標準のY-upへ変換。Web側は固定軸ではなくRest Poseの骨位置から座標差を算出
- Draco圧縮は不使用。約422KBで、iPhone Safari互換性を優先

## 出力ファイル

- `rigged_hand.glb`: 431,696 bytes
- `dist/rigged_hand.blend`: Rest Pose
- `dist/rigged_hand_test.blend`: 9ポーズテスト付き
- `dist/rigging_validation.json`: 自動検証値

## 検証結果

- Blender 5.1.1で配布GLB読込と再書き出しに成功
- `AnatomicalHandRig_R`、22骨、Skin、Armature Modifierを確認
- `AnatomicalHandMesh_R`は5,248頂点・4,370ポリゴン
- 全頂点にウェイトあり。GLB内の未正規化ウェイト行なし
- `AnatomicalHandSurface`と`UVMap`を保持
- GLB内部の数値、骨名、Skin、ウェイト正規化を `tools/verify_glb.py` で検査
- Three.jsでGLB読込、必須17骨取得、22骨の骨表示を確認
- 390×844縦画面と844×390横画面のデモ表示を確認
- 現在のローカルページのブラウザコンソールerror／warningは0件

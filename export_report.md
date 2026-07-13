# GLB書き出し・検証レポート

## 出力条件

- Blender 4.5.9 LTS
- GLB 2.0、単一メッシュ、Skinあり、17 Joints
- 材質2、UV保持、外部テクスチャなし
- カメラ、ライト、原本バックアップはGLBへ含めない
- Rest Poseを書き出し、テストアニメーションはWeb用GLBから除外
- glTF標準のY-upへ変換。Web側は固定軸ではなくRest Poseの骨位置から座標差を算出
- Draco圧縮は不使用。約278KBと十分小さく、iPhone Safari互換性を優先

## 出力ファイル

- `rigged_hand.glb`: 284,536 bytes
- `dist/rigged_hand.blend`: Rest Pose
- `dist/rigged_hand_test.blend`: 9ポーズテスト付き
- `dist/rigging_validation.json`: 自動検証値

## 検証結果

- Blender 4.5.9へGLB再読込成功
- `MediaPipeHand_R`、17骨、Skin、Armature Modifierを確認
- `RiggedHandMesh`は4,416頂点・7,600ポリゴン
- 全頂点にウェイトあり。負ウェイト、1超過ウェイトなし
- `CrystalSkin`、`CrystalNail`、`UVMap`を保持
- GLB内部の数値、骨名、Skin、ウェイト正規化を `tools/verify_glb.py` で検査
- Three.jsでGLB読込と17骨取得を確認
- ブラウザコンソールのerror／warningは0件

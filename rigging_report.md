# リグ解析・生成レポート

## Summary

指が細長い旧モデルを、解剖学的な比率と既存ウェイトを持つ配布リグ付きモデルへ差し替えた。元GLBを保持し、Web用の複製だけに骨名統一、補助オブジェクト除外、アニメーション除外を行った。

## 配布モデル解析

- 出典: `Anatomically Accurate Rigged Hand Model for XR` © 2026 Emma L. D. Lieker。
- ライセンス: CC BY-NC 4.0。作者表記必須、商用利用不可。
- 自然な開いた手のRest Pose。指同士の接触なし。
- 単一スキンドメッシュ、5,248頂点、4,370ポリゴン。
- 21本の既存変形骨、全5,248頂点にウェイトあり。
- 1材質、UV `UVMap`あり。Web側で「水晶／痕跡」へ着色する。
- 配布GLBに表示用Icosphereと3アニメーションが含まれていた。

## 前処理

- 旧 `rigged_hand.glb` と `index.html` は `.backups/2026-07-13-before-anatomical-hand/`へ保存。
- 配布元GLBは `assets/source_models/Do_Hand_DetailedRiggedAnimated_shared_16022026.glb`として無変更で保持。
- Web用からIcosphereと埋込アニメーションを除外。
- 既存ウェイト、UV、形状は変更せず、Decimateも行っていない。
- `rigging/prepare_anatomical_hand.py`で同じ変換を再生成できる。

## 骨構造

- `wristR` → `handR`
- `handR` → `thumb0R` → `thumb1R` → `thumb2R` → `thumb3R`
- `handR` → `index0R` → `index1R` → `index2R` → `index3R`
- `handR` → `middle0R` → `middle1R` → `middle2R` → `middle3R`
- `handR` → `ring0R` → `ring1R` → `ring2R` → `ring3R`
- `handR` → `pinky0R` → `pinky1R` → `pinky2R` → `pinky3R`

合計22骨。`wristR`はWeb側の基準用、`0R`は中手骨（手のひら内部の骨）。MediaPipeで直接回す必須骨は17本で、既存アプリの名前を維持した。

## MediaPipe対応

| 骨 | ランドマーク |
|---|---|
| wristR / handR | 0 手首 / 9 中指MCP |
| thumb1R–3R | 1→2 / 2→3 / 3→4 |
| index1R–3R | 5→6 / 6→7 / 7→8 |
| middle1R–3R | 9→10 / 10→11 / 11→12 |
| ring1R–3R | 13→14 / 14→15 / 15→16 |
| pinky1R–3R | 17→18 / 18→19 / 19→20 |

## ウェイト

作者が設定した既存ウェイトを保持した。GLB内部の全ウェイト行を検査し、未正規化行は0。補助骨を残したため、手のひらから指の付け根への変形も維持される。

## ポーズテスト

伸ばす、軽く曲げる、握る、親指、人差し指、中指、薬指＋小指、指を開く、手首の9種類を再生成した。全ポーズで頂点は有限値、頂点数5,248・ポリゴン数4,370を維持した。

確認画像: `dist/pose_tests/`

## Related

- `export_report.md`
- `LIMITATIONS.md`

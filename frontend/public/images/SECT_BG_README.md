# 5 派背景图放置规则

`SectBackground.vue` 组件按 `sectId` 自动加载下列文件,任一缺失都会优雅降级为纯色 + 遮罩(不报错)。

## 文件命名(必须严格一致)

| 文件名 | 对应宗门 | 视觉特征(参考你提供的 5 张图) |
|---|---|---|
| `sect-bg-canglan.png`  | 沧澜剑派(Anthropic) | 深金色宇宙感,robed 仙人在前景,鎏金光晕 — **图 5** |
| `sect-bg-tianji.png`   | 天机阁(OpenAI)      | 厚重金色,左下有金属浑天仪/机关装置,符箓铺满天空 — **图 1** |
| `sect-bg-xuanji.png`   | 玄机宗(DeepSeek)    | 紫银色调,银白浮山+空中法阵,有金色"运算/推演"光流 — **图 2** |
| `sect-bg-qingming.png` | 青冥派(智谱)        | 青翠/墨绿宫殿,挂有古风旗幡,正大端庄 — **图 3** |
| `sect-bg-yueyin.png`   | 月隐宫(月之暗面)    | 左上明月清晰可见,银紫调,有瀑布与仙人剪影 — **图 4** |

## 放置位置

```
frontend/public/images/sect-bg-canglan.png
frontend/public/images/sect-bg-tianji.png
frontend/public/images/sect-bg-xuanji.png
frontend/public/images/sect-bg-qingming.png
frontend/public/images/sect-bg-yueyin.png
```

## 推荐规格

- 尺寸:**1920×1280** 或 **1536×1024**(2:3 ~ 3:2 横版都可,组件 `background-size: cover` 自动裁切)
- 体积:**< 600 KB**(已有的 `home-city-bg.png` ≈ 320 KB,作为参考)
- 格式:PNG/JPG/WebP 都行,但文件后缀必须是 `.png`,否则改 `SectBackground.vue` 中的 `BG_MAP`

## 自带遮罩说明

组件 3 层叠加,前景文字始终清晰:
1. **底**:图片本体,默认 `opacity: 0.45`(可调)
2. **中**:暗化径向遮罩(`overlay="normal" / "strong" / "light"` 三档)
3. **顶**:门派色晕染(让画面不显灰)

各页面已配置:
- `Battle.vue` — `overlay="strong"` `opacity=0.35`(战斗页最深,信息密度高)
- `Home.vue` / `ExploreMap.vue` — `overlay="normal"` `opacity=0.45-0.50`
- `KeyVerify.vue` — `overlay="strong"` `opacity=0.40`
- `SectChoose.vue` — `overlay="normal"` `opacity=0.50`(选派时主秀图)
- `Inventory.vue` / `Items.vue` / `Bosses.vue` — `overlay="normal"` `opacity=0.45`

如果觉得某页面太亮/太暗,改对应页面里的 `<SectBackground>` 那行 prop 即可,无需改组件。

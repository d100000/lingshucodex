# 修仙画像资产清单

本清单由 `scripts/generate_xianxia_assets.py` 生成。画像统一为 512x768 PNG,进入游戏背景为 1920x1080 PNG。

## 资产生成硬性规则

所有正式头像、人物立绘、NPC 画像必须使用 `gpt-image-2` 生成。禁止使用本地占位绘制器、程序化几何头像或 SVG 占位图冒充正式资产。

五宗弟子 200 人头像使用:

```text
scripts/generate_disciple_image2_portraits.py
```

`scripts/generate_disciple_assets.py` 只负责从文档抽取数据并生成 `frontend/src/data/disciples.json`,不得生成正式头像。

## 数量

- 宗门画像: 5
- 主角画像: 45
- 怪物画像: 113
- Boss 画像: 21
- 背景图: 1
- 总计: 185

## 保存位置

- 宗门: `frontend/public/images/portraits/sects/{sect_id}.png`
- 主角: `frontend/public/images/portraits/players/{sect_id}/{realm}.png`
- 怪物: `frontend/public/images/portraits/enemies/{enemy_id}.png`
- Boss: `frontend/public/images/portraits/bosses/{boss_id}.png`
- 进入游戏背景: `frontend/public/images/backgrounds/entry-bg.png`
- JSON manifest: `frontend/public/images/portraits/manifest.json`

## 宗门与主角

- 沧澜剑派 `canglan`: 宗门图 `/images/portraits/sects/canglan.png`, 主角境界 9 张: 炼气、筑基、金丹、元婴、化神、合体、大乘、渡劫、飞升
- 天机阁 `tianji`: 宗门图 `/images/portraits/sects/tianji.png`, 主角境界 9 张: 炼气、筑基、金丹、元婴、化神、合体、大乘、渡劫、飞升
- 玄机宗 `xuanji`: 宗门图 `/images/portraits/sects/xuanji.png`, 主角境界 9 张: 炼气、筑基、金丹、元婴、化神、合体、大乘、渡劫、飞升
- 青冥派 `qingming`: 宗门图 `/images/portraits/sects/qingming.png`, 主角境界 9 张: 炼气、筑基、金丹、元婴、化神、合体、大乘、渡劫、飞升
- 月隐宫 `yueyin`: 宗门图 `/images/portraits/sects/yueyin.png`, 主角境界 9 张: 炼气、筑基、金丹、元婴、化神、合体、大乘、渡劫、飞升

## 怪物画像

- 山林狐妖族: 10 张, 山林小狐、石板狐、双尾赤狐、三尾灵狐、四尾狐婢、五尾媚妖、六尾天狐、七尾狐圣…
- 灵雀飞鸟族: 10 张, 小灵雀、彩翎雀、金喙隼、幻翼蝶、雷击鹰、孔雀仙翎、鹰王、凤雏…
- 蛇蟒族: 10 张, 水蛇、草丛青蛇、毒齿乌蛇、山蟒、毒蟒王、九头蛇魔、白蟒精、玄武之裔…
- 猛兽族: 9 张, 幼狼、灰狼、山豹、雪豹仙、怒虎、金毛獬豸、白虎魂、虎王相柳…
- 草木精怪族: 9 张, 灵芝童子、藤蔓魔、桃花妖、丹木老人、百花娘子、千年树王、人参精、灵芝祖宗…
- 鬼族: 9 张, 野鬼、怨灵、厉鬼、阴煞鬼将、无头将军、牛头马面、白无常、黑无常…
- 龙族: 9 张, 蛟、蜃龙、螭龙、应龙、螳螂龙、墨龙、青龙、祖龙残魂…
- 神兽族: 10 张, 朱雀雏、玄武幼龟、白虎兽、青龙幼苗、麒麟驹、孔雀明王坐骑、九尾天狐(神兽级)、应龙正神…
- 上古凶兽族: 10 张, 穷奇幼崽、饕餮、梼杌、混沌、九婴、相柳、蚩尤之灵、夸父之心…
- 魔修族: 9 张, 迷心人、嗜血修、傀儡师、夺魂者、黑袍人、魔尊化身、嗜灵狂魔、魔界使者…
- 仙器之灵族: 9 张, 断剑残魂、古镜怨灵、玉佩仙子、金钟巨灵、墨笔仙翁、九鼎之灵、天瓶之灵、炼丹炉魂…
- 异域生灵族: 9 张, 异界刺客、迷雾行者、晶族战士、深渊使徒、时间游者、维度割裂者、星河使者、造物之主使徒…

## Boss 画像

- 墨魔·林泽 `boss_canglan_traitor`: 沧澜叛徒 · Lv.40 · `/images/portraits/bosses/boss_canglan_traitor.png`
- 齿轮鬼·托马斯 `boss_tianji_traitor`: 天机叛徒 · Lv.42 · `/images/portraits/bosses/boss_tianji_traitor.png`
- 哈萨长老 `boss_deepmind`: 深玄阁阁主 · Lv.110 · `/images/portraits/bosses/boss_deepmind.png`
- 阿莫迪克斯 `boss_canglan_supreme`: 沧澜山主 · Lv.145 · `/images/portraits/bosses/boss_canglan_supreme.png`
- 山姆道君 `boss_tianji_supreme`: 天机阁掌教 · Lv.148 · `/images/portraits/bosses/boss_tianji_supreme.png`
- 拥抱真人 `boss_huggingface`: 拥抱观观主 · Lv.78 · `/images/portraits/bosses/boss_huggingface.png`
- 米斯特拉 `boss_mistral`: 风暴宗宗主 · Lv.85 · `/images/portraits/bosses/boss_mistral.png`
- 舟翁·维平 `boss_together`: 同舟会盟主 · Lv.72 · `/images/portraits/bosses/boss_together.png`
- 衍化老人 `boss_replicate`: 衍化盟盟主 · Lv.68 · `/images/portraits/bosses/boss_replicate.png`
- 稳心圣女·艾玛 `boss_stability`: 持心门当代掌门 · Lv.63 · `/images/portraits/bosses/boss_stability.png`
- 王小川·百川海主 `boss_baichuan`: 百川海主 · Lv.80 · `/images/portraits/bosses/boss_baichuan.png`
- 李开峰 `boss_yi_kaifu`: 万物峰祖师 · Lv.90 · `/images/portraits/bosses/boss_yi_kaifu.png`
- 姜大昕·阶星仙翁 `boss_step`: 阶星阁阁主 · Lv.88 · `/images/portraits/bosses/boss_step.png`
- 闫极道祖 `boss_minimax`: 微极派祖师 · Lv.82 · `/images/portraits/bosses/boss_minimax.png`
- 商汤大圣 `boss_sensetime`: 商汤殿殿主 · Lv.92 · `/images/portraits/bosses/boss_sensetime.png`
- 玄道魔主·马克丝 `boss_xai_grok`: 玄道宫宫主 · Lv.120 · `/images/portraits/bosses/boss_xai_grok.png`
- 迷踪散人 `boss_perplexity`: 迷踪派主 · Lv.76 · `/images/portraits/bosses/boss_perplexity.png`
- 转折天尊·里德 `boss_inflection`: 转折宫主 · Lv.70 · `/images/portraits/bosses/boss_inflection.png`
- 千面舞者·诺姆 `boss_character_mask`: 千面殿主 · Lv.66 · `/images/portraits/bosses/boss_character_mask.png`
- 极速僧·乔纳森 `boss_groq`: 极速门门主 · Lv.74 · `/images/portraits/bosses/boss_groq.png`
- 界外神祇 `boss_final_void`: 跨界至高存在 · Lv.180 · `/images/portraits/bosses/boss_final_void.png`

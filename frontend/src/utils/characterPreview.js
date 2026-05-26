import discipleData from '../data/disciples.json'

export const CHARACTER_PREVIEW_EVENT = 'lingshu:character-preview'
const CORE_SECTS = new Set(['canglan', 'tianji', 'xuanji', 'qingming', 'yueyin'])
const REALM_IDS = new Set(['qi', 'foundation', 'golden', 'yuanying', 'huashen', 'hetishi', 'dacheng', 'dujie', 'feisheng'])
const DISCIPLE_BY_ID = Object.fromEntries(discipleData.disciples.map(d => [d.id, d]))
const SECTS = discipleData.sects

function coreSectId(id) {
  return CORE_SECTS.has(id) ? id : ''
}

export function openCharacterPreview(profile) {
  if (!profile || typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(CHARACTER_PREVIEW_EVENT, { detail: normalizeProfile(profile) }))
}

function normalizeProfile(profile) {
  return {
    kind: profile.kind || '角色',
    id: profile.id || '',
    name: profile.name || '无名之辈',
    title: profile.title || '',
    subtitle: profile.subtitle || '',
    portrait: profile.portrait || null,
    sectId: coreSectId(profile.sectId || profile.sect_id || profile.sect || ''),
    accent: profile.accent || '#D4A24C',
    tags: profile.tags || [],
    stats: profile.stats || [],
    background: profile.background || '',
    bonds: profile.bonds || [],
    histories: profile.histories || [],
    interactions: profile.interactions || [],
    archive: profile.archive || [],
    sections: profile.sections || [],
  }
}

function sectAccent(sectId) {
  const color = SECTS[sectId]?.color || [212, 162, 76]
  return `rgb(${color.join(',')})`
}

function relationLabel(affinity) {
  if (affinity >= 80) return '生死之交'
  if (affinity >= 60) return '至交'
  if (affinity >= 35) return '信重旧识'
  if (affinity >= 15) return '友善'
  if (affinity > -15) return '点头之交'
  if (affinity > -35) return '芥蒂'
  if (affinity > -60) return '争执旧识'
  if (affinity > -80) return '怨敌'
  return '宿敌'
}

function pairKey(a, b) {
  return `${a}__${b}`
}

function relationFromWorld(world, sourceId, targetId, fallback = {}) {
  const rel = world?.relations?.[pairKey(sourceId, targetId)]
  return {
    affinity: rel?.affinity ?? fallback.affinity ?? 0,
    relation: rel?.tags?.[0] || fallback.relation || relationLabel(rel?.affinity ?? fallback.affinity ?? 0),
    recent: rel?.recent || [],
    history: rel?.history || [],
  }
}

export function disciplePreview(actorOrId, world = null) {
  const id = typeof actorOrId === 'string' ? actorOrId : actorOrId?.id
  const d = DISCIPLE_BY_ID[id]
  if (!d) return null
  const state = world?.disciples?.[id] || {}
  const level = state.level || d.level
  const ageYears = Math.max(1, Math.floor((state.age_days || d.base_age_years * 360) / 360))
  const status = state.status?.length ? state.status.join('、') : '平稳'

  const baseBonds = (d.relationships || [])
    .filter(r => DISCIPLE_BY_ID[r.target_id])
    .slice(0, 8)
    .map(r => {
      const rel = relationFromWorld(world, id, r.target_id, r)
      const target = DISCIPLE_BY_ID[r.target_id]
      return {
        name: target?.name || r.target_name || r.target_id,
        relation: `${rel.relation} · 好感 ${rel.affinity}`,
        desc: rel.recent?.[0] || r.relation || '这段羁绊仍在江湖中发酵。',
      }
    })

  const dynamicBonds = world?.relations
    ? Object.entries(world.relations)
      .filter(([key]) => key.startsWith(`${id}__`))
      .map(([key, rel]) => {
        const targetId = key.split('__')[1]
        const target = DISCIPLE_BY_ID[targetId]
        if (!target) return null
        return {
          name: target.name,
          relation: `${rel.tags?.[0] || relationLabel(rel.affinity || 0)} · 好感 ${rel.affinity || 0}`,
          desc: rel.recent?.[0] || '近期暂无明面交集。',
        }
      })
      .filter(Boolean)
    : []

  const bondNames = new Set()
  const bonds = baseBonds.concat(dynamicBonds)
    .filter(b => {
      const key = `${b.name}:${b.relation}`
      if (bondNames.has(key)) return false
      bondNames.add(key)
      return true
    })
    .slice(0, 10)

  const allHistory = (state.history?.length ? state.history : state.recent || [])
    .map(item => ({
      title: item.major ? `大事 · ${item.label}` : (item.label || '江湖轶事'),
      meta: item.day ? `第 ${item.day} 日` : '旧闻',
      body: item.summary || item.text || '卷宗只留下了一行模糊记录。',
    }))

  const relationHistory = world?.relations
    ? Object.entries(world.relations)
      .filter(([key]) => key.startsWith(`${id}__`) || key.endsWith(`__${id}`))
      .flatMap(([, rel]) => rel.history || rel.recent || [])
      .slice(0, 40)
      .map((text, index) => ({
        title: '羁绊记录',
        meta: `关系 ${index + 1}`,
        body: typeof text === 'string' ? text : (text.summary || '关系卷宗未详。'),
      }))
    : []

  const archive = allHistory.concat(relationHistory)

  return normalizeProfile({
    kind: '五宗弟子',
    id,
    name: d.name,
    title: `${d.sect_name || SECTS[d.sect_id]?.name || '未知宗门'} · ${d.rank}`,
    subtitle: `${d.gender || '未知'} · ${ageYears} 岁 · Lv.${level}`,
    accent: sectAccent(d.sect_id),
    sectId: coreSectId(d.sect_id),
    portrait: {
      kind: 'disciple',
      id: d.portrait_id || `${d.sect_id}/${d.id}`,
      shape: 'card',
    },
    tags: [d.rank, d.personality, `Lv.${level}`, status].filter(Boolean),
    stats: [
      { label: '等级', value: level },
      { label: '年龄', value: `${ageYears} 岁` },
      { label: '身份', value: d.rank },
      { label: '状态', value: status },
      { label: '宗门', value: d.sect_name || SECTS[d.sect_id]?.name || d.sect_id },
    ],
    background: `${d.appearance || '外貌未详'}。${d.story_hook || '此人的故事仍藏在江湖暗处。'}`,
    bonds,
    histories: archive.slice(0, 3),
    archive,
  })
}

function compactStats(stats = {}) {
  return [
    ['气血', stats.hp ?? stats.max_hp],
    ['攻击', stats.atk],
    ['防御', stats.def_],
    ['速度', stats.spd],
    ['闪避', stats.evasion != null ? `${Math.round(stats.evasion * 100)}%` : null],
    ['暴击', stats.crit_rate != null ? `${Math.round(stats.crit_rate * 100)}%` : null],
  ].filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => ({ label, value }))
}

function normalizeBonds(bonds = []) {
  return bonds.map((bond, index) => ({
    name: bond.target_name || bond.name || bond.target_id || `因果 ${index + 1}`,
    relation: bond.relation || bond.type || '羁绊',
    desc: bond.desc || bond.description || '这段因果尚未完全写入卷宗。',
  }))
}

export function npcPortraitRef(npc = {}, shape = 'card') {
  const portraitId = npc.portrait_id || ''
  const tail = portraitId.split('/').pop()
  const inferredKind = portraitId && !REALM_IDS.has(tail) ? 'disciple' : 'player'
  return {
    kind: npc.portrait_kind || inferredKind,
    id: portraitId || `${npc.sect_id || npc.sect || 'canglan'}/${npc.realm || 'qi'}`,
    shape,
  }
}

export function enemyPortraitRef(enemy = {}, shape = 'card') {
  if (enemy.is_npc) return npcPortraitRef(enemy, shape)
  if (enemy.portrait_kind && enemy.portrait_id) {
    return { kind: enemy.portrait_kind, id: enemy.portrait_id, shape }
  }
  if (enemy.tier === 'boss' || String(enemy.id || '').startsWith('boss_')) {
    return { kind: 'boss', id: enemy.id || '', shape }
  }
  return { kind: 'enemy', id: enemy.id || '', shape }
}

export function playerPreview(character = {}) {
  const sectName = character.sect_name || '散修'
  const realmName = character.realm_name || '未入境'
  const histories = (character.battle_history || []).slice(-8).reverse().map((battle) => ({
    title: battle.enemy_name || '未知对手',
    meta: battle.result === 'victory' ? '胜' : battle.result === 'defeat' ? '败' : '退',
    body: `${battle.round_count || 0} 回合 · ${battle.enemy_clan || '未知族群'}`,
  }))

  const interactions = (character.fortune_log || []).slice(-6).reverse().map((f) => ({
    title: f.name || '无名奇遇',
    meta: f.type || '奇遇',
    body: [
      f.applied?.hp_delta ? `气血 ${f.applied.hp_delta > 0 ? '+' : ''}${f.applied.hp_delta}` : '',
      f.applied?.exp_delta ? `修为 ${f.applied.exp_delta > 0 ? '+' : ''}${f.applied.exp_delta}` : '',
      f.applied?.drop_name || '',
    ].filter(Boolean).join(' · '),
  }))

  return normalizeProfile({
    kind: '主角',
    id: character.id || character.user_id || 'player',
    name: character.name || '执笔者',
    title: `${sectName} · ${realmName}`,
    subtitle: `Lv.${character.level || 1}`,
    accent: '#D4A24C',
    sectId: coreSectId(character.sect || 'canglan'),
    portrait: {
      kind: 'player',
      id: `${character.sect || 'canglan'}/${character.realm || 'qi'}`,
      shape: 'card',
    },
    tags: [sectName, realmName, `Lv.${character.level || 1}`],
    stats: [
      { label: '气血', value: `${character.hp || 0}/${character.max_hp || 0}` },
      { label: '灵气', value: `${character.qi || 0}/${character.max_qi || 0}` },
      { label: '修为', value: character.exp || 0 },
      { label: '疲劳', value: `${character.fatigue || 0}/${character.max_fatigue || 80}` },
      { label: '攻击', value: character.atk || 0 },
      { label: '防御', value: character.def_ || 0 },
      { label: '速度', value: character.spd || 0 },
      { label: '暴击', value: `${Math.round((character.crit_rate || 0) * 100)}%` },
    ],
    background: character.background_story || character.story || `${character.name || '执笔者'}拜入${sectName},以本命书载道,以燃灵成章增长修为。`,
    bonds: Object.entries(character.factions || {}).map(([sect, value]) => ({
      name: sect,
      relation: value >= 50 ? '挚友' : value >= 20 ? '友善' : value >= 0 ? '陌路' : '敌对',
      desc: `当前人缘 ${value}`,
    })),
    histories,
    interactions,
    sections: character.blessings?.length ? [{
      title: '拜入机缘',
      items: character.blessings.map((b) => ({
        title: `${b.attr_icon || ''} ${b.note || b.attr_name}`,
        body: `${b.attr_name || '资质'} +${b.delta || 0}`,
      })),
    }] : [],
  })
}

export function bossPreview(boss = {}, options = {}) {
  const sect = options.sect || {}
  const bondMap = options.bossMap || {}
  const bonds = (boss.bonds || []).map((bond, index) => {
    const targetId = typeof bond === 'string' ? bond : bond.target_id
    const target = bondMap[targetId]
    return {
      name: target?.name || targetId,
      relation: '羁绊',
      desc: typeof bond === 'object'
        ? bond.desc
        : (boss.bond_descriptions?.[index] || '因果未明,仍在卷宗中等待补完。'),
    }
  })

  return normalizeProfile({
    kind: '道君',
    id: boss.id,
    name: boss.name,
    title: boss.title,
    subtitle: `${boss.sect_name || sect.name || '散修'} · Lv.${boss.level || 1}`,
    accent: sect.base_color || options.accent || '#FFD700',
    sectId: coreSectId(boss.sect_id || sect.id || ''),
    portrait: { kind: 'boss', id: boss.id, shape: 'card' },
    tags: [boss.sect_name || sect.name || '散修', boss.company || sect.company || '', `Lv.${boss.level || 1}`].filter(Boolean),
    stats: compactStats(boss),
    background: boss.lore,
    bonds,
    histories: [
      boss.signature_skill ? { title: '标志性招式', meta: '战斗', body: boss.signature_skill } : null,
      sect.real_background ? { title: '真实背景', meta: sect.company || '宗派', body: sect.real_background } : null,
      sect.sect_story ? { title: '宗派演绎', meta: sect.name || '宗派', body: sect.sect_story } : null,
    ].filter(Boolean),
    interactions: boss.drops?.length ? [{
      title: '可能掉落',
      meta: '战利品',
      body: boss.drops.join('、'),
    }] : [],
  })
}

export function enemyPreview(enemy = {}, bestiary = null) {
  const interactions = []
  if (bestiary) {
    interactions.push(
      { title: '遭遇次数', meta: '图鉴', body: String(bestiary.encountered || 0) },
      { title: '击杀次数', meta: '图鉴', body: String(bestiary.defeated || 0) },
      { title: '成功赠礼', meta: '图鉴', body: String(bestiary.gifted || 0) },
    )
    if (bestiary.first_kill_at) {
      interactions.push({ title: '首杀时间', meta: '图鉴', body: bestiary.first_kill_at })
    }
  }

  const signature = enemy.signature_skill
  const attributes = (enemy.attributes || []).map((item) => ({
    title: item.name,
    body: item.value,
  }))
  const traits = (enemy.traits || []).map((item) => ({
    title: item.name,
    body: item.effect || item.desc,
  }))
  const skills = (enemy.skills || []).slice(0, 5).map((skill) => ({
    title: `${skill.name}${skill.tier_name ? ` · ${skill.tier_name}` : ''}`,
    body: skill.description || skill.effect || '族谱未详。',
  }))

  return normalizeProfile({
    kind: enemy.is_npc ? '修士' : '妖兽',
    id: enemy.id,
    name: enemy.name,
    title: enemy.title || enemy.clan,
    subtitle: `${enemy.battle_role || enemy.temperament || ''} · Lv.${enemy.level || 1}`,
    accent: enemy.is_npc ? '#7FC7E8' : '#C03F3F',
    sectId: coreSectId(enemy.sect_id || ''),
    portrait: enemyPortraitRef(enemy, 'card'),
    tags: [enemy.clan, enemy.tier, enemy.element, enemy.weakness ? `弱点: ${enemy.weakness}` : '', `Lv.${enemy.level || 1}`].filter(Boolean),
    stats: compactStats(enemy),
    background: enemy.full_lore || enemy.lore || enemy.description,
    bonds: normalizeBonds(enemy.bonds || []),
    histories: [
      enemy.description ? { title: '外貌与传闻', meta: '传闻', body: enemy.description } : null,
      signature ? { title: '专属技能', meta: signature.tier_name || '本命', body: `${signature.name}: ${signature.description || signature.effect}` } : null,
      enemy.unique_hook ? { title: '独特性', meta: '怪物志', body: enemy.unique_hook } : null,
      enemy.drops?.length ? { title: '已知掉落', meta: '战利品', body: enemy.drops.join('、') } : null,
    ].filter(Boolean),
    interactions,
    sections: [
      attributes.length ? { title: '怪物属性', items: attributes } : null,
      traits.length ? { title: '特性', items: traits } : null,
      skills.length ? { title: '招式谱', items: skills } : null,
    ].filter(Boolean),
  })
}

export function npcPreview(npc = {}) {
  return enemyPreview({
    ...npc,
    is_npc: true,
    clan: npc.clan || `${npc.sect_name || ''}弟子`,
    lore: npc.lore || `${npc.name || '这名修士'}出身${npc.sect_name || '未知门派'},位列${npc.rank || '弟子'},此番在山野中与你相逢。`,
    bonds: [{
      name: npc.sect_name || npc.sect_id || '未知门派',
      relation: npc.intent_label || npc.intent || '相逢',
      desc: npc.description || '一次尚未写入本命书的江湖照面。',
    }],
  })
}

/**
 * 案件种子数据 - 浏览器控制台脚本
 *
 * 用法：打开 Tauri 应用的 DevTools (F12)，
 * 粘贴本文件全部内容并回车，然后刷新页面。
 */

function seedMatters() {
  const genId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
  const now = Date.now()
  const DAY = 86400000
  const t = (da) => new Date(now - da * DAY)

  // 清除旧数据
  localStorage.removeItem('lawclaw_matters')

  const matters = []

  // ════════════════════════════════════════════
  // 1. 华盛公司与明远公司借贷合同纠纷
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '华盛公司与明远公司借贷合同纠纷',
    caseNumber: '(2026)沪0105民初8273号', client: '华盛贸易有限公司',
    counterparty: '明远建设工程有限公司', practiceArea: '合同纠纷',
    stage: '诉讼中', deadline: t(30).toISOString(),
    courtName: '上海市长宁区人民法院', courtDate: t(-15).toISOString(),
    description: '2025年3月，华盛公司与明远公司签订《借款合同》，约定出借500万元，借款期限6个月，年利率12%。明远公司以名下房产抵押担保。借款到期后经多次催讨，明远公司仅支付三个月利息，本金及剩余利息未付。',
    caseType: 'civil', opposingCounsel: '郑国辉 律师',
    createdAt: t(180), updatedAt: new Date(),
    customCategories: ['案件文书', '证据材料', '对方提交', '法院文书'],
  })

  // ════════════════════════════════════════════
  // 2. 张某诉李某离婚纠纷
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '张某诉李某离婚纠纷',
    caseNumber: '(2026)京0105民初4621号', client: '张某（女方）',
    counterparty: '李某（男方）', practiceArea: '婚姻家庭',
    stage: '诉讼中',
    courtName: '北京市朝阳区人民法院', courtDate: t(-10).toISOString(),
    description: '张女士与李先生于2018年登记结婚，婚后育有一子（5岁）。因李先生长期忙于工作、缺乏家庭沟通，双方感情逐渐冷淡。张女士主张：解除婚姻关系，婚生子由女方抚养男方按月支付抚养费5000元，分割婚后共同财产（住房一套、存款80万元、车辆一辆），并要求男方支付精神损害赔偿10万元。男方不同意离婚，认为感情尚未破裂。',
    caseType: 'civil', opposingCounsel: '方芳 律师',
    createdAt: t(120), updatedAt: new Date(),
    customCategories: ['婚姻家庭', '证据材料', '财产清单', '法院文书', '对方提交'],
  })

  // ════════════════════════════════════════════
  // 3. 周某诉王某民间借贷纠纷
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '周某诉王某民间借贷纠纷',
    caseNumber: '(2026)粤0304民初12568号', client: '周建军',
    counterparty: '王海明', practiceArea: '民间借贷',
    stage: '证据收集', deadline: t(25).toISOString(),
    courtName: '深圳市福田区人民法院',
    description: '2024年8月，王某因生意周转需要向周某借款80万元，约定借款期限6个月，月息1.5%，王某出具了借条。借款后王某仅支付了2个月利息，之后便以各种理由推脱。2025年6月起王某失联，周某多方寻找未果。现委托我所通过诉讼途径追回欠款本息共计约95万元。目前正在收集证据准备立案。',
    caseType: 'civil',
    createdAt: t(60), updatedAt: new Date(),
    customCategories: ['借贷证据', '案件文书', '对方信息', '法院文书'],
  })

  // ════════════════════════════════════════════
  // 4. 天行科技诉蓝海公司专利侵权纠纷（知识产权）
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '天行科技公司诉蓝海科技公司发明专利侵权纠纷',
    caseNumber: '(2026)最高法知民终189号', client: '天行科技股份有限公司',
    counterparty: '蓝海科技（深圳）有限公司', practiceArea: '知识产权',
    stage: '诉讼中', deadline: t(60).toISOString(),
    courtName: '最高人民法院知识产权法庭', courtDate: t(20).toISOString(),
    description: '天行科技系名称为"基于人工智能的图像识别方法与系统"（专利号：ZL202310xxxxxx.x）的发明专利权人。天行科技发现蓝海公司制造销售的"蓝海AI视觉检测系统"落入其专利权利要求保护范围。一审法院判决构成侵权，赔偿300万元。蓝海公司不服一审判决，向最高人民法院提起上诉。本案为二审阶段。',
    caseType: 'civil', opposingCounsel: '陈思远 律师',
    createdAt: t(365), updatedAt: new Date(),
    customCategories: ['专利文件', '侵权证据', '法律文书', '技术文档', '对方提交'],
  })

  // ════════════════════════════════════════════
  // 5. 交通事故人身损害赔偿
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '赵某诉钱某交通事故人身损害赔偿纠纷',
    caseNumber: '(2026)京0115民初3692号', client: '赵晓东（受害方）',
    counterparty: '钱大军、长兴财险北京分公司', practiceArea: '交通事故',
    stage: '调解中', deadline: t(35).toISOString(),
    courtName: '北京市大兴区人民法院', courtDate: t(-5).toISOString(),
    description: '2025年12月15日，钱大军驾驶小客车将骑电动车的赵晓东撞伤。经交警认定钱大军负全部责任。赵晓东诊断为左胫腓骨开放性骨折、脑震荡，住院32天，花费医疗费8.6万元，构成十级伤残。肇事车辆投保于长兴财险。起诉要求赔偿医疗费、误工费、伤残赔偿金等共计38.6万元。目前法院正在组织调解。',
    caseType: 'civil', opposingCounsel: '刘文杰 律师（长兴财险）',
    createdAt: t(90), updatedAt: new Date(),
    customCategories: ['案件文书', '医疗证据', '事故证据', '保险材料', '赔偿清单'],
  })

  // ════════════════════════════════════════════
  // 6. 劳动争议案
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '孙某诉辉煌科技有限公司违法解除劳动合同纠纷',
    caseNumber: '京劳人仲字(2026)第1582号', client: '孙丽华（员工）',
    counterparty: '辉煌科技有限公司', practiceArea: '劳动争议',
    stage: '审查中', deadline: t(50).toISOString(),
    courtName: '北京市劳动人事争议仲裁委员会', courtDate: t(10).toISOString(),
    description: '孙丽华于2018年3月入职辉煌科技，任产品经理，月薪2.5万元。2025年底公司以"组织架构调整"为由将其裁减，未提前30日通知，也未支付N+1补偿。孙丽华主张违法解除要求支付赔偿金2N（40万元）、未休年假折算5.8万元、年终奖8万元、加班费3.2万元。公司主张合法裁员仅同意支付20万元。已进入劳动仲裁阶段。',
    caseType: 'civil', opposingCounsel: '林立峰 法务（辉煌科技）',
    createdAt: t(45), updatedAt: new Date(),
    customCategories: ['案件文书', '劳动合同', '工资证据', '加班证据', '公司文件'],
  })

  // ════════════════════════════════════════════
  // 7. 房屋买卖合同纠纷（集体诉讼）
  // ════════════════════════════════════════════
  matters.push({
    id: genId(), title: '吴某等32户业主诉宏远地产房屋买卖合同纠纷（集体诉讼）',
    caseNumber: '(2026)京0108民初21037号', client: '吴建华等32户业主',
    counterparty: '宏远地产集团北京有限公司', practiceArea: '房产纠纷',
    stage: '证据收集', deadline: t(40).toISOString(),
    courtName: '北京市海淀区人民法院',
    description: '32户业主购买海淀区"宏远华府"项目，合同约定2024年12月31日前交房。截至2026年项目停工超18个月。开发商以资金链断裂为由多次延期。业主集体委托维权，拟诉请继续履行合同并支付逾期交房违约金，或解除合同返还购房款及利息。目前正在收集证据，准备诉前财产保全。',
    caseType: 'civil', opposingCounsel: '宏远法务团队',
    createdAt: t(30), updatedAt: new Date(),
    customCategories: ['购房合同', '付款证据', '沟通记录', '法律文书', '集体诉讼'],
  })

  localStorage.setItem('lawclaw_matters', JSON.stringify(matters))
  console.log('✅ 已写入 ' + matters.length + ' 个案件数据到 localStorage')
  console.log('📋 案件列表：')
  matters.forEach((m, i) => console.log('   ' + (i+1) + '. ' + m.title + ' (' + m.stage + ')'))
  console.log('🔄 现在刷新页面即可看到效果 → Cmd/Ctrl + R')
}

seedMatters()

/**
 * 一键种子数据脚本
 * 在浏览器控制台粘贴运行，然后刷新页面
 */
(function() {
  const genId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
  const now = Date.now()
  const DAY = 86400000
  const t = (da) => new Date(now - da * DAY)

  // ════════════════════════════════════════
  // 1. 案件数据
  // ════════════════════════════════════════
  const MATTERS_KEY = 'lawclaw_matters'
  const matters = []

  // 1. 华盛公司借贷合同纠纷
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

  // 2. 张某诉李某离婚纠纷
  matters.push({
    id: genId(), title: '张某诉李某离婚纠纷',
    caseNumber: '(2026)京0105民初4621号', client: '张某（女方）',
    counterparty: '李某（男方）', practiceArea: '婚姻家庭',
    stage: '诉讼中',
    courtName: '北京市朝阳区人民法院', courtDate: t(-10).toISOString(),
    description: '张女士与李先生于2018年登记结婚，婚后育有一子（5岁）。张女士主张解除婚姻关系，婚生子由女方抚养，分割婚后共同财产（住房一套、存款80万元、车辆一辆），并要求精神损害赔偿10万元。男方不同意离婚。',
    caseType: 'civil', opposingCounsel: '方芳 律师',
    createdAt: t(120), updatedAt: new Date(),
    customCategories: ['婚姻家庭', '证据材料', '财产清单', '法院文书'],
  })

  // 3. 周某诉王某民间借贷纠纷
  matters.push({
    id: genId(), title: '周某诉王某民间借贷纠纷',
    caseNumber: '(2026)粤0304民初12568号', client: '周建军',
    counterparty: '王海明', practiceArea: '民间借贷',
    stage: '证据收集', deadline: t(25).toISOString(),
    courtName: '深圳市福田区人民法院',
    description: '2024年8月，王某向周某借款80万元，月息1.5%。借款后王某仅支付2个月利息后失联。现委托追回欠款本息约95万元。正在收集证据准备立案。',
    caseType: 'civil',
    createdAt: t(60), updatedAt: new Date(),
    customCategories: ['借贷证据', '案件文书', '对方信息'],
  })

  // 4. 天行科技专利侵权纠纷
  matters.push({
    id: genId(), title: '天行科技公司诉蓝光科技公司发明专利侵权纠纷',
    caseNumber: '(2026)最高法知民终189号', client: '天行科技股份有限公司',
    counterparty: '蓝光科技（深圳）有限公司', practiceArea: '知识产权',
    stage: '诉讼中', deadline: t(60).toISOString(),
    courtName: '最高人民法院知识产权法庭', courtDate: t(20).toISOString(),
    description: '天行科技发现蓝光公司制造的"蓝光AI视觉检测系统"侵犯其AI图像识别发明专利。一审判决蓝光公司停止侵权、赔偿300万元。蓝光公司上诉至最高院。本案为二审阶段。',
    caseType: 'civil', opposingCounsel: '陈思远 律师',
    createdAt: t(365), updatedAt: new Date(),
    customCategories: ['专利文件', '侵权证据', '法律文书', '技术文档'],
  })

  // 5. 交通事故人身损害赔偿
  matters.push({
    id: genId(), title: '赵某诉钱某交通事故人身损害赔偿纠纷',
    caseNumber: '(2026)京0115民初3692号', client: '赵晓东（受害方）',
    counterparty: '钱大军、平安财险北京分公司', practiceArea: '交通事故',
    stage: '调解中', deadline: t(35).toISOString(),
    courtName: '北京市大兴区人民法院', courtDate: t(-5).toISOString(),
    description: '钱大军驾车将赵晓东撞伤，负全部责任。赵晓东住院32天，医疗费8.6万元，构成十级伤残。起诉要求赔偿38.6万元。法院正组织调解。',
    caseType: 'civil', opposingCounsel: '刘文杰 律师（平安财险）',
    createdAt: t(90), updatedAt: new Date(),
    customCategories: ['案件文书', '医疗证据', '事故证据', '保险材料', '赔偿清单'],
  })

  // 6. 劳动争议
  matters.push({
    id: genId(), title: '孙某诉辉煌科技有限公司违法解除劳动合同纠纷',
    caseNumber: '京劳人仲字(2026)第1582号', client: '孙丽华（员工）',
    counterparty: '辉煌科技有限公司', practiceArea: '劳动争议',
    stage: '审查中', deadline: t(50).toISOString(),
    courtName: '北京市劳动人事争议仲裁委员会', courtDate: t(10).toISOString(),
    description: '孙丽华工作近8年被公司以"组织架构调整"为由裁减，未提前30日通知。主张违法解除赔偿金2N=40万元、未休年假折算5.8万元等。已进入劳动仲裁阶段。',
    caseType: 'civil', opposingCounsel: '林立峰 法务（辉煌科技）',
    createdAt: t(45), updatedAt: new Date(),
    customCategories: ['案件文书', '劳动合同', '工资证据', '加班证据'],
  })

  // 7. 房屋买卖合同集体诉讼
  matters.push({
    id: genId(), title: '吴某等32户业主诉恒大地产房屋买卖合同纠纷（集体诉讼）',
    caseNumber: '(2026)京0108民初21037号', client: '吴建华等32户业主',
    counterparty: '恒大地产集团北京有限公司', practiceArea: '房产纠纷',
    stage: '证据收集', deadline: t(40).toISOString(),
    courtName: '北京市海淀区人民法院',
    description: '32户业主购买恒大华府项目，合同约定2024年底交房。项目停工超18个月。业主集体委托维权，拟诉请继续履行合同或解除合同返还购房款。正在收集证据。',
    caseType: 'civil', opposingCounsel: '恒大法务团队',
    createdAt: t(30), updatedAt: new Date(),
    customCategories: ['购房合同', '付款证据', '沟通记录', '法律文书'],
  })

  localStorage.setItem(MATTERS_KEY, JSON.stringify(matters))
  console.log('✅ 已写入 ' + matters.length + ' 个案件')

  // ════════════════════════════════════════
  // 2. 日程数据
  // ════════════════════════════════════════
  const base = new Date(2026, 6, 7, 8, 0, 0)
  const D = 86400000, H = 3600000
  const td = (d, h, m = 0) => new Date(+base + d * D + h * H + m * 60000).toISOString()
  const items = []

  // 今日
  items.push({ id: genId(), title: '与张伟案当事人会见', dateTime: td(0,9,0), endDateTime: td(0,10,30), type: 'meeting', completed: false, note: '讨论交通事故赔偿方案', createdAt: td(-3,14) })
  items.push({ id: genId(), title: '提交陈芳案代理词（最后期限）', dateTime: td(0,12,0), type: 'deadline', completed: false, note: '劳动仲裁案，中午前提交', createdAt: td(-5,9) })
  items.push({ id: genId(), title: '东城区法院调取证据', dateTime: td(0,14,0), endDateTime: td(0,16,0), type: 'appointment', completed: false, note: '调取工商登记信息', createdAt: td(-2,10) })
  items.push({ id: genId(), title: '团队案件讨论会', dateTime: td(0,16,30), endDateTime: td(0,17,30), type: 'meeting', completed: false, note: '讨论下周三个开庭案件策略', createdAt: td(-1,9) })
  items.push({ id: genId(), title: '健身', dateTime: td(0,18,30), endDateTime: td(0,19,30), type: 'personal', completed: false, note: '律所楼下健身房', createdAt: td(-7,8) })

  // 本周
  items.push({ id: genId(), title: '李梅房产继承案调解', dateTime: td(1,9,30), endDateTime: td(1,11,0), type: 'court', completed: false, note: '朝阳区法院 第3调解室', createdAt: td(-10,11) })
  items.push({ id: genId(), title: '审查王刚案证据材料', dateTime: td(1,14,0), endDateTime: td(1,17,0), type: 'meeting', completed: false, note: '梳理28份证据', createdAt: td(-4,16) })
  items.push({ id: genId(), title: '刘洋案二审上诉状截止', dateTime: td(2,17,0), type: 'deadline', completed: false, note: '最后一天提交上诉状', createdAt: td(-20,10) })
  items.push({ id: genId(), title: '会见取保候审当事人赵强', dateTime: td(2,9,0), endDateTime: td(2,11,0), type: 'appointment', completed: false, note: '海淀区看守所', createdAt: td(-6,14) })
  items.push({ id: genId(), title: '律所合伙人会议', dateTime: td(3,10,0), endDateTime: td(3,12,0), type: 'meeting', completed: false, note: '讨论季度营收', createdAt: td(-14,9) })
  items.push({ id: genId(), title: '宋氏继承纠纷案开庭', dateTime: td(3,14,0), endDateTime: td(3,17,0), type: 'court', completed: false, note: '西城区法院 第8法庭', createdAt: td(-30,9) })
  items.push({ id: genId(), title: '送检笔迹鉴定材料', dateTime: td(4,9,0), endDateTime: td(4,10,0), type: 'appointment', completed: false, note: '司法鉴定中心', createdAt: td(-3,15) })
  items.push({ id: genId(), title: '整理下周开庭材料', dateTime: td(4,14,0), endDateTime: td(4,18,0), type: 'personal', completed: false, note: '准备三个案件开庭提纲', createdAt: td(-2,11) })
  items.push({ id: genId(), title: '周末值班电话咨询', dateTime: td(5,9,0), endDateTime: td(5,12,0), type: 'meeting', completed: false, note: '律所值班', createdAt: td(-7,8) })

  // 下周
  items.push({ id: genId(), title: '林达公司买卖合同纠纷开庭', dateTime: td(6,9,0), endDateTime: td(6,12,0), type: 'court', completed: false, note: '深圳南山区法院 第5法庭', createdAt: td(-25,14) })
  items.push({ id: genId(), title: '公证处网页保全', dateTime: td(6,14,0), endDateTime: td(6,16,0), type: 'appointment', completed: false, note: '侵权网页保全公证', createdAt: td(-8,10) })
  items.push({ id: genId(), title: '王磊诈骗案案情分析会', dateTime: td(7,10,0), endDateTime: td(7,12,0), type: 'meeting', completed: false, note: '与刑事部同事讨论', createdAt: td(-4,16) })
  items.push({ id: genId(), title: '提交周敏案证据交换材料', dateTime: td(7,17,0), type: 'deadline', completed: false, note: '证据交换截止日', createdAt: td(-12,9) })
  items.push({ id: genId(), title: '顾问单位华兴科技回访', dateTime: td(8,9,30), endDateTime: td(8,11,30), type: 'meeting', completed: false, note: '审查新合同模板', createdAt: td(-5,11) })
  items.push({ id: genId(), title: '仲裁案庭前会议', dateTime: td(9,14,0), endDateTime: td(9,16,0), type: 'court', completed: false, note: '北京仲裁委员会 第2庭', createdAt: td(-15,13) })
  items.push({ id: genId(), title: '缴纳诉讼费截止', dateTime: td(10,17,0), type: 'deadline', completed: false, note: '华盛公司案', createdAt: td(-18,9) })
  items.push({ id: genId(), title: '张老先生遗嘱拟写（上门）', dateTime: td(11,9,0), endDateTime: td(11,12,0), type: 'appointment', completed: false, note: '朝阳区上门', createdAt: td(-6,10) })
  items.push({ id: genId(), title: '知识产权讲座PPT准备', dateTime: td(11,14,0), endDateTime: td(11,17,0), type: 'personal', completed: false, note: '企业IP保护讲座', createdAt: td(-10,15) })
  items.push({ id: genId(), title: '亲子日——带孩子科技馆', dateTime: td(12,10,0), endDateTime: td(12,16,0), type: 'personal', completed: false, note: '', createdAt: td(-3,20) })

  // 更远日程
  items.push({ id: genId(), title: '黄某人身损害赔偿案开庭', dateTime: td(13,9,0), endDateTime: td(13,12,0), type: 'court', completed: false, note: '海淀区法院 第12法庭', createdAt: td(-20,11) })
  items.push({ id: genId(), title: '公司并购尽调汇报', dateTime: td(14,10,0), endDateTime: td(14,12,0), type: 'meeting', completed: false, note: '向客户汇报5项风险', createdAt: td(-9,14) })
  items.push({ id: genId(), title: '提交质证意见截止', dateTime: td(15,17,0), type: 'deadline', completed: false, note: '针对12份证据', createdAt: td(-7,10) })
  items.push({ id: genId(), title: '赴天津调取工商档案', dateTime: td(16,8,0), endDateTime: td(16,17,0), type: 'appointment', completed: false, note: '查对方变更记录', createdAt: td(-11,9) })
  items.push({ id: genId(), title: '建设工程合同纠纷鉴定质证', dateTime: td(18,9,0), endDateTime: td(18,12,0), type: 'court', completed: false, note: '丰台区法院 第6法庭', createdAt: td(-30,10) })
  items.push({ id: genId(), title: '律所团建——怀柔青龙湖', dateTime: td(19,8,0), endDateTime: td(19,18,0), type: 'personal', completed: false, note: '漂流+烧烤', createdAt: td(-14,9) })
  items.push({ id: genId(), title: '涉外案件研讨会（远程）', dateTime: td(21,14,0), endDateTime: td(21,16,0), type: 'meeting', completed: false, note: 'Zoom与香港联营所', createdAt: td(-10,11) })
  items.push({ id: genId(), title: '陈某某受贿罪一审开庭', dateTime: td(24,9,0), endDateTime: td(24,17,0), type: 'court', completed: false, note: '北京市一中院 第3法庭', createdAt: td(-40,9) })
  items.push({ id: genId(), title: '年中工作总结报告提交', dateTime: td(26,18,0), type: 'deadline', completed: false, note: '向管委会提交', createdAt: td(-5,14) })
  items.push({ id: genId(), title: '法律援助中心值班', dateTime: td(28,9,0), endDateTime: td(28,17,0), type: 'appointment', completed: false, note: '东城区法援中心', createdAt: td(-20,8) })

  // 已完成
  items.push({ id: genId(), title: '赵某欠款纠纷案开庭', dateTime: td(-2,9,0), endDateTime: td(-2,11,0), type: 'court', completed: true, note: '对方同意调解', createdAt: td(-20,10) })
  items.push({ id: genId(), title: '提交管辖权异议申请书', dateTime: td(-3,17,0), type: 'deadline', completed: true, note: '已按时提交', createdAt: td(-10,9) })
  items.push({ id: genId(), title: '与审计师对接财务数据', dateTime: td(-4,14,0), endDateTime: td(-4,16,0), type: 'appointment', completed: true, note: '完成数据交接', createdAt: td(-8,11) })
  items.push({ id: genId(), title: '新人合同审查培训', dateTime: td(-5,10,0), endDateTime: td(-5,12,0), type: 'meeting', completed: true, note: '已结束', createdAt: td(-12,9) })
  items.push({ id: genId(), title: '年度体检', dateTime: td(-7,8,0), endDateTime: td(-7,12,0), type: 'personal', completed: true, note: '', createdAt: td(-30,9) })

  // 多日跨越
  items.push({ id: genId(), title: '上海出差——调查取证', dateTime: td(20,8,0), endDateTime: td(22,18,0), type: 'appointment', completed: false, note: '浦东法院、工商局调证', createdAt: td(-15,14) })
  items.push({ id: genId(), title: '破产管理人会议（3天）', dateTime: td(30,9,0), endDateTime: td(32,17,0), type: 'meeting', completed: false, note: '房地产公司破产清算案', createdAt: td(-20,10) })
  items.push({ id: genId(), title: '全天撰写并购法律意见书', dateTime: td(23,8,0), endDateTime: td(23,19,0), type: 'personal', completed: false, note: '客户催得急', createdAt: td(-3,17) })
  items.push({ id: genId(), title: '全市律师业务培训（全天）', dateTime: td(27,8,0), endDateTime: td(27,18,0), type: 'meeting', completed: false, note: '市律协年度继续教育', createdAt: td(-25,9) })

  localStorage.setItem('lawclaw_schedule', JSON.stringify(items))
  console.log('✅ 已写入 ' + items.length + ' 条日程')

  console.log('🔄 现在刷新页面即可看到所有数据 → Cmd/Ctrl+R')
})()

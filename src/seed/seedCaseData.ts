import type { Matter, MatterStage } from '../types/legal'
import type { Ref } from 'vue'

export function seedAllDemoCases(
  matters: Ref<Matter[]>,
  saveMatters: (m: Matter[]) => void,
  tl: { events: any[] },
  fs: { files: any[] },
) {
  // ── Helpers ──
  const now = Date.now()
  const DAY = 86400000
  const t = (da: number) => new Date(now - da * DAY)

  function svgDataUrl(label: string): string {
    const ext = label.split('.').pop() || ''
    const s = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="260"><rect width="200" height="260" fill="#f8f9fa" rx="8"/><rect x="20" y="20" width="160" height="8" rx="4" fill="#1a2744"/><rect x="20" y="40" width="120" height="8" rx="4" fill="#c9a84c"/><line x1="40" y1="80" x2="160" y2="80" stroke="#d0d2db" stroke-width="1"/><rect x="20" y="95" width="160" height="4" rx="2" fill="#e4e5ec"/><rect x="20" y="107" width="140" height="4" rx="2" fill="#e4e5ec"/><rect x="20" y="119" width="150" height="4" rx="2" fill="#e4e5ec"/><rect x="20" y="131" width="100" height="4" rx="2" fill="#e4e5ec"/><line x1="40" y1="155" x2="160" y2="155" stroke="#d0d2db" stroke-width="1"/><text x="100" y="200" text-anchor="middle" font-size="14" fill="#5a5a7a">' + label + '</text><text x="100" y="225" text-anchor="middle" font-size="11" fill="#8e8ea0">' + ext + '</text></svg>'
    return 'data:image/svg+xml;utf8,' + encodeURIComponent(s)
  }

  function addFiles(mId: string, seedList: string[][]) {
    for (const [name, cat] of seedList) {
      const data = svgDataUrl(name)
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
      fs.files.unshift({ id, name, size: data.length, type: '', category: cat as any, matterId: mId, createdAt: new Date(), data })
    }
  }

  function addTimeline(mId: string, events: Array<{ type: string; title: string; desc: string; da: number }>) {
    for (const ev of events) {
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
      tl.events.unshift({ id, matterId: mId, type: ev.type as any, title: ev.title, description: ev.desc, createdAt: t(ev.da), createdBy: 'system' as const })
    }
  }

  function addMatter(m: {
    title: string; caseNumber: string; client: string; counterparty?: string;
    practiceArea: string; stage: MatterStage; deadline?: string; courtName?: string;
    courtDate?: string; description: string; caseType?: 'civil' | 'criminal' | 'administrative' | 'commercial' | 'other';
    opposingCounsel?: string; da: number; categories?: string[];
  }): string {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
    matters.value.unshift({
      id, title: m.title, caseNumber: m.caseNumber, client: m.client,
      counterparty: m.counterparty, practiceArea: m.practiceArea,
      stage: m.stage, deadline: m.deadline, courtName: m.courtName,
      courtDate: m.courtDate, description: m.description,
      caseType: m.caseType, opposingCounsel: m.opposingCounsel,
      createdAt: t(m.da), updatedAt: new Date(),
      customCategories: m.categories ?? ['案件文书', '证据材料', '其他'],
    })
    saveMatters(matters.value)
    return id
  }

  // ════════════════════════════════════════════
  // 1. 华盛公司与明远公司借贷合同纠纷（已有）
  // ════════════════════════════════════════════
  const m1 = addMatter({
    title: '华盛公司与明远公司借贷合同纠纷',
    caseNumber: '(2026)沪0105民初8273号', client: '华盛贸易有限公司',
    counterparty: '明远建设工程有限公司', practiceArea: '合同纠纷',
    stage: '诉讼中', deadline: t(-20).toISOString(),
    courtName: '上海市长宁区人民法院', courtDate: t(-15).toISOString(),
    description: '2025年3月，华盛公司与明远公司签订《借款合同》，约定出借500万元，借款期限6个月，年利率12%。明远公司以名下房产抵押担保。借款到期后经多次催讨，明远公司仅支付三个月利息，本金及剩余利息未付。',
    caseType: 'civil', opposingCounsel: '郑国辉 律师', da: 180,
    categories: ['案件文书', '证据材料', '对方提交', '法院文书'],
  })
  addTimeline(m1, [
    { type: 'milestone', title: '借贷交易完成', desc: '华盛公司向明远公司发放贷款500万元', da: 540 },
    { type: 'milestone', title: '首次利息支付', desc: '明远公司支付第一个月利息5万元', da: 510 },
    { type: 'milestone', title: '第三期利息逾期', desc: '明远公司未按期支付第三期利息', da: 420 },
    { type: 'note', title: '发送催收函（第一次）', desc: '要求15日内清偿欠款本息', da: 360 },
    { type: 'note', title: '发送催收函（第二次）', desc: '告知将启动诉讼程序', da: 330 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '开始审查合同及证据材料', da: 300 },
    { type: 'note', title: '财产保全申请', desc: '申请查封明远公司名下房产及银行账户', da: 290 },
    { type: 'milestone', title: '法院裁定准予保全', desc: '长宁区人民法院准予查封冻结', da: 280 },
    { type: 'file_upload', title: '证据材料整理完成', desc: '28份证据材料整理编号', da: 270 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 诉讼中', desc: '向法院提交立案材料', da: 260 },
    { type: 'milestone', title: '法院正式立案', desc: '案号 (2026)沪0105民初8273号', da: 250 },
    { type: 'court_date', title: '首次开庭通知', desc: '开庭日期2026年5月15日', da: 230 },
    { type: 'court_date', title: '首次开庭审理', desc: '明远公司承认借款事实，主张利息过高', da: 180 },
    { type: 'note', title: '代理词提交', desc: '援引民间借贷司法解释论述利率争议', da: 175 },
    { type: 'court_date', title: '第二次开庭（调解）', desc: '因分歧过大，调解失败', da: 150 },
    { type: 'deadline', title: '审判期限临近', desc: '审理期限即将届满', da: 45 },
    { type: 'milestone', title: '庭后补充代理意见', desc: '提交针对性反驳意见', da: 30 },
  ])
  addFiles(m1, [
    ['起诉状.docx','案件文书'], ['证据清单.docx','案件文书'], ['代理词.docx','案件文书'],
    ['利息计算明细表.xlsx','证据材料'], ['损失清单.xlsx','证据材料'],
    ['借款合同.pdf','证据材料'], ['银行转账凭证.pdf','证据材料'], ['抵押登记证明.pdf','证据材料'],
    ['法院传票.pdf','法院文书'], ['判决书.pdf','法院文书'],
    ['案件分析报告.md','AI生成'], ['法律意见书.md','AI生成'],
    ['证据照片.jpg','证据材料'], ['现场示意图.png','证据材料'],
  ])

  // ════════════════════════════════════════════
  // 2. 张某诉李某离婚纠纷（离婚案）
  // ════════════════════════════════════════════
  const m2 = addMatter({
    title: '张某诉李某离婚纠纷',
    caseNumber: '(2026)京0105民初4621号', client: '张某（女方）',
    counterparty: '李某（男方）', practiceArea: '婚姻家庭',
    stage: '诉讼中', deadline: undefined,
    courtName: '北京市朝阳区人民法院', courtDate: t(-10).toISOString(),
    description: '张女士与李先生于2018年登记结婚，婚后育有一子（5岁）。因李先生长期忙于工作、缺乏家庭沟通，双方感情逐渐淡漠。张女士主张：1）解除婚姻关系；2）婚生子由女方抚养，男方按月支付抚养费5000元；3）分割婚后共同财产（住房一套、存款80万元、车辆一辆）；4）要求男方支付精神损害赔偿10万元。男方不同意离婚，认为感情尚未破裂。',
    caseType: 'civil', opposingCounsel: '方芳 律师', da: 120,
    categories: ['婚姻家庭', '证据材料', '财产清单', '法院文书', '对方提交'],
  })
  addTimeline(m2, [
    { type: 'milestone', title: '张女士首次到所咨询', desc: '初步了解婚姻状况和财产情况', da: 150 },
    { type: 'milestone', title: '正式签订委托代理合同', desc: '委托离婚诉讼及财产分割', da: 140 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '收集结婚证、房产证、银行流水等材料', da: 135 },
    { type: 'file_upload', title: '财产证据收集完成', desc: '整理双方名下财产清单及凭证', da: 130 },
    { type: 'note', title: '撰写起诉状', desc: '起草离婚起诉状及财产分割清单', da: 125 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 诉讼中', desc: '向朝阳区法院提交立案材料', da: 120 },
    { type: 'milestone', title: '法院正式立案', desc: '案号 (2026)京0105民初4621号', da: 115 },
    { type: 'note', title: '收集男方收入证据', desc: '申请法院调查令调取男方近三年收入记录', da: 100 },
    { type: 'note', title: '保全申请', desc: '申请查封登记在男方名下的共同房产，防止转移', da: 95 },
    { type: 'milestone', title: '法院裁定保全', desc: '朝阳法院准予查封房产', da: 90 },
    { type: 'court_date', title: '首次开庭（调解）', desc: '男方不同意离婚，法庭调解未果', da: 60 },
    { type: 'note', title: '提交补充证据', desc: '提交男方与第三者微信聊天记录等过错证据', da: 55 },
    { type: 'court_date', title: '第二次开庭', desc: '双方就孩子抚养权激烈辩论', da: 30 },
    { type: 'milestone', title: '庭后调解方案沟通', desc: '男方松口同意离婚，但财产分割争议大', da: 15 },
    { type: 'note', title: '提交代理词', desc: '围绕感情破裂、抚养权归属、过错赔偿三条主线', da: 10 },
    { type: 'deadline', title: '等待判决', desc: '预计下月初作出一审判决', da: -5 },
  ])
  addFiles(m2, [
    ['民事起诉状.docx','案件文书'], ['离婚证据清单.xlsx','证据材料'], ['授权委托书.pdf','案件文书'],
    ['结婚证扫描件.pdf','证据材料'], ['房产证复印件.pdf','证据材料'], ['车辆登记证.pdf','证据材料'],
    ['银行流水明细.pdf','证据材料'], ['男方收入证明.pdf','证据材料'],
    ['微信聊天记录.pdf','对方提交'], ['通话录音文字稿.docx','对方提交'],
    ['孩子出生证明.pdf','证据材料'], ['抚养费计算表.xlsx','财产清单'],
    ['财产分割方案.docx','案件文书'], ['代理词.docx','案件文书'],
    ['法院传票.pdf','法院文书'], ['保全裁定书.pdf','法院文书'],
  ])

  // ════════════════════════════════════════════
  // 3. 周某诉王某民间借贷纠纷
  // ════════════════════════════════════════════
  const m3 = addMatter({
    title: '周某诉王某民间借贷纠纷',
    caseNumber: '(2026)粤0304民初12568号', client: '周建军',
    counterparty: '王海明', practiceArea: '民间借贷',
    stage: '证据收集', deadline: t(-3).toISOString(),
    courtName: '深圳市福田区人民法院', courtDate: undefined,
    description: '2024年8月，王某因生意周转需要向周某借款80万元，约定借款期限6个月，月息1.5%，王某出具了借条。借款后王某仅支付了2个月利息，之后便以各种理由推脱。2025年6月起王某失联，周某多方寻找未果。现委托我所通过诉讼途径追回欠款本息共计约95万元。目前正在收集证据准备立案。',
    caseType: 'civil', opposingCounsel: undefined, da: 60,
    categories: ['借贷证据', '案件文书', '对方信息', '法院文书'],
  })
  addTimeline(m3, [
    { type: 'milestone', title: '当事人到所咨询', desc: '周某持借条复印件到所咨询追款路径', da: 70 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '审查借条、转账记录等核心证据', da: 65 },
    { type: 'milestone', title: '签订风险代理合同', desc: '约定回款后按15%收取代理费', da: 62 },
    { type: 'note', title: '向王某发送律师函', desc: '要求3日内清偿欠款本息', da: 58 },
    { type: 'note', title: '律师函退回', desc: '王某地址变更，快递退回，对方有意躲避', da: 55 },
    { type: 'note', title: '查询王某身份信息', desc: '通过公安机关查询王某最新户籍及居住信息', da: 52 },
    { type: 'note', title: '查询王某名下财产', desc: '发现王某名下无房产、车辆，银行账户余额不足千元', da: 48 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 证据收集', desc: '核心证据已齐，需补强证明借款实际交付', da: 45 },
    { type: 'file_upload', title: '银行转账凭证调取', desc: '向银行调取80万元转账流水原始凭证', da: 40 },
    { type: 'file_upload', title: '微信催款记录导出', desc: '导出并公证微信聊天记录23页', da: 35 },
    { type: 'milestone', title: '了解王某其他债权人', desc: '另有3人也起诉了王某，总欠款约200万元', da: 28 },
    { type: 'note', title: '准备财产保全材料', desc: '尽可能查找王某隐匿财产线索', da: 20 },
    { type: 'note', title: '撰写起诉状', desc: '诉讼请求：偿还借款本金80万+利息15万', da: 15 },
    { type: 'deadline', title: '计划本周内立案', desc: '待补充王某最新居住证明后提交立案', da: 3 },
  ])
  addFiles(m3, [
    ['民事起诉状.docx','案件文书'], ['借条扫描件.pdf','借贷证据'], ['转账凭证.pdf','借贷证据'],
    ['银行流水.pdf','借贷证据'], ['微信聊天记录.pdf','借贷证据'],
    ['律师函（副本）.pdf','案件文书'], ['催款记录.xlsx','借贷证据'],
    ['王某身份信息查询.pdf','对方信息'], ['财产查询回执.pdf','对方信息'],
    ['案件分析报告.md','AI生成'],
    ['利息计算表.xlsx','案件文书'], ['诉讼风险评估报告.md','AI生成'],
  ])

  // ════════════════════════════════════════════
  // 4. 天行科技诉蓝光公司专利侵权纠纷（知识产权案）
  // ════════════════════════════════════════════
  const m4 = addMatter({
    title: '天行科技公司诉蓝光科技公司发明专利侵权纠纷',
    caseNumber: '(2026)最高法知民终189号', client: '天行科技股份有限公司',
    counterparty: '蓝光科技（深圳）有限公司', practiceArea: '知识产权',
    stage: '诉讼中', deadline: t(60).toISOString(),
    courtName: '最高人民法院知识产权法庭', courtDate: t(-7).toISOString(),
    description: '天行科技系名称为"基于人工智能的图像识别方法与系统"（专利号：ZL202310xxxxxx.x）的发明专利权人。该专利于2023年获得授权，涉及AI图像识别核心技术。天行科技发现蓝光公司制造销售的"蓝光AI视觉检测系统"落入其专利权利要求保护范围，未经许可实施其专利技术。天行科技诉请：1）停止侵权；2）赔偿经济损失及合理开支共计500万元；3）销毁侵权产品和专用模具。一审法院判决构成侵权，赔偿300万元。蓝光公司不服一审判决，向最高人民法院提起上诉。本案为二审阶段。',
    caseType: 'civil', opposingCounsel: '陈思远 律师', da: 365,
    categories: ['专利文件', '侵权证据', '法律文书', '技术文档', '对方提交'],
  })
  addTimeline(m4, [
    { type: 'milestone', title: '天行科技发现侵权线索', desc: '市场部门在展会上发现蓝光公司疑似侵权产品', da: 420 },
    { type: 'note', title: '购买侵权产品取证', desc: '公证购买蓝光AI视觉检测系统一套', da: 410 },
    { type: 'file_upload', title: '侵权产品技术分析', desc: '委托第三方机构反向分析侵权产品技术方案', da: 400 },
    { type: 'milestone', title: '专利侵权比对报告完成', desc: '确认蓝光产品落入权利要求1-5保护范围', da: 390 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '开始评估诉讼可行性和赔偿预期', da: 385 },
    { type: 'milestone', title: '签订委托代理合同', desc: '天行科技委托我所全权代理诉讼', da: 375 },
    { type: 'note', title: '发送侵权警告函', desc: '要求蓝光公司停止侵权并协商赔偿', da: 370 },
    { type: 'note', title: '蓝光公司回函否认侵权', desc: '主张自有技术和专利不同，拒绝协商', da: 360 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 诉讼中', desc: '向广州知识产权法院提起诉讼', da: 355 },
    { type: 'milestone', title: '案件受理', desc: '广州知识产权法院正式立案', da: 350 },
    { type: 'milestone', title: '证据交换', desc: '双方交换技术文档和侵权对比证据', da: 300 },
    { type: 'court_date', title: '一审开庭审理', desc: '技术调查官参与，庭前会议确定技术事实争议焦点', da: 270 },
    { type: 'note', title: '技术鉴定申请', desc: '申请法院委托鉴定机构就技术方案是否等同进行鉴定', da: 260 },
    { type: 'milestone', title: '鉴定报告出具', desc: '鉴定结论：两者技术手段、功能、效果实质相同', da: 220 },
    { type: 'court_date', title: '一审第二次开庭', desc: '围绕鉴定报告进行质证', da: 200 },
    { type: 'milestone', title: '一审宣判', desc: '判决蓝光公司停止侵权，赔偿天行科技300万元', da: 150 },
    { type: 'note', title: '蓝光公司提起上诉', desc: '蓝光公司不服一审判决，向最高院知识产权法庭上诉', da: 135 },
    { type: 'stage_change', title: '阶段变更: 诉讼中 → 诉讼中（二审）', desc: '转入最高院二审程序', da: 130 },
    { type: 'file_upload', title: '二审答辩状提交', desc: '针对上诉理由逐一反驳', da: 120 },
    { type: 'note', title: '二审庭前会议', desc: '最高院组织远程视频庭前会议', da: 60 },
    { type: 'deadline', title: '二审开庭', desc: '预计下周在最高院知识产权法庭开庭', da: 20 },
  ])
  addFiles(m4, [
    ['发明专利证书.pdf','专利文件'], ['专利权利要求书.pdf','专利文件'], ['专利说明书.pdf','专利文件'],
    ['侵权比对表.xlsx','侵权证据'], ['侵权产品照片.zip','侵权证据'], ['公证购买记录.pdf','侵权证据'],
    ['技术鉴定报告.pdf','技术文档'], ['反向分析报告.pdf','技术文档'],
    ['民事起诉状.docx','法律文书'], ['证据清单.docx','法律文书'],
    ['一审判决书.pdf','法律文书'], ['二审上诉状（对方）.pdf','对方提交'],
    ['二审答辩状.docx','法律文书'], ['代理词.docx','法律文书'],
    ['索赔计算明细.xlsx','案件文书'], ['案件时间线.md','AI生成'],
  ])

  // ════════════════════════════════════════════
  // 5. 赵某诉钱某交通事故人身损害赔偿案
  // ════════════════════════════════════════════
  const m5 = addMatter({
    title: '赵某诉钱某交通事故人身损害赔偿纠纷',
    caseNumber: '(2026)京0115民初3692号', client: '赵晓东（受害方）',
    counterparty: '钱大军、平安财险北京分公司', practiceArea: '交通事故',
    stage: '调解中', deadline: t(-12).toISOString(),
    courtName: '北京市大兴区人民法院', courtDate: t(-5).toISOString(),
    description: '2025年12月15日，钱大军驾驶京Axxxxx号小客车在大兴区黄亦路将骑电动车的赵晓东撞伤。经交警认定，钱大军未保持安全车距负全部责任。赵晓东被送往大兴区人民医院治疗，诊断为：左胫腓骨开放性骨折、脑震荡、多处软组织挫伤，住院32天，花费医疗费8.6万元。经司法鉴定构成十级伤残。肇事车辆投保于平安财险北京分公司。因协商赔偿未果，现起诉要求赔偿医疗费、误工费、护理费、伤残赔偿金、精神损害抚慰金等共计38.6万元。目前法院正在组织调解。',
    caseType: 'civil', opposingCounsel: '刘文杰 律师（平安财险）', da: 90,
    categories: ['案件文书', '医疗证据', '事故证据', '保险材料', '赔偿清单'],
  })
  addTimeline(m5, [
    { type: 'milestone', title: '事故发生', desc: '钱大军驾车追尾赵晓东电动车', da: 210 },
    { type: 'note', title: '交通责任认定', desc: '大兴交通支队出具认定书：钱大军全责', da: 205 },
    { type: 'milestone', title: '当事人到所咨询', desc: '赵晓东家属到所咨询赔偿事宜', da: 180 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '收集事故认定书、病历等材料', da: 175 },
    { type: 'milestone', title: '签订委托代理合同', desc: '风险代理，约定回款后收费', da: 170 },
    { type: 'note', title: '调取肇事车辆保险信息', desc: '确认平安财险为承保公司', da: 165 },
    { type: 'file_upload', title: '医疗病历收集', desc: '收集住院病历、诊断证明、费用清单', da: 160 },
    { type: 'file_upload', title: '申请伤残鉴定', desc: '委托法大法庭科学技术鉴定所鉴定', da: 150 },
    { type: 'milestone', title: '鉴定结论出具', desc: '十级伤残，误工期120天，护理期60天', da: 130 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 诉讼中', desc: '向大兴法院提起诉讼', da: 120 },
    { type: 'milestone', title: '法院立案', desc: '案号 (2026)京0115民初3692号', da: 115 },
    { type: 'note', title: '与保险公司初步沟通', desc: '平安财险认可责任，但对赔偿金额分歧较大', da: 80 },
    { type: 'court_date', title: '开庭审理', desc: '三方到庭，法庭辩论后建议调解', da: 45 },
    { type: 'note', title: '赔偿方案协商', desc: '平安财险报价24万元，我方要求35万元', da: 40 },
    { type: 'stage_change', title: '阶段变更: 诉讼中 → 调解中', desc: '双方均同意在法庭主持下调解', da: 35 },
    { type: 'note', title: '提交调解方案', desc: '让步至30万元，含精神损害抚慰金2万元', da: 20 },
    { type: 'milestone', title: '调解有望', desc: '保险公司内部审批28万元方案，预计本周答复', da: 5 },
  ])
  addFiles(m5, [
    ['民事起诉状.docx','案件文书'], ['授权委托书.pdf','案件文书'],
    ['事故认定书.pdf','事故证据'], ['驾驶证行驶证复印件.pdf','事故证据'], ['现场照片.jpg','事故证据'],
    ['住院病历.pdf','医疗证据'], ['诊断证明.pdf','医疗证据'], ['医疗费发票.pdf','医疗证据'],
    ['伤残鉴定报告.pdf','医疗证据'], ['误工证明.pdf','赔偿清单'],
    ['赔偿清单.xlsx','赔偿清单'], ['计算明细表.xlsx','赔偿清单'],
    ['保险单.pdf','保险材料'], ['保险公司调解方案.pdf','对方提交'],
    ['代理词.docx','案件文书'],
  ])

  // ════════════════════════════════════════════
  // 6. 孙某诉辉煌公司劳动争议案
  // ════════════════════════════════════════════
  const m6 = addMatter({
    title: '孙某诉辉煌科技有限公司违法解除劳动合同纠纷',
    caseNumber: '京劳人仲字(2026)第1582号', client: '孙丽华（员工）',
    counterparty: '辉煌科技有限公司', practiceArea: '劳动争议',
    stage: '审查中', deadline: t(50).toISOString(),
    courtName: '北京市劳动人事争议仲裁委员会', courtDate: t(-10).toISOString(),
    description: '孙丽华于2018年3月入职辉煌科技，任产品经理，月薪2.5万元。2025年底公司以"组织架构调整"为由将其裁减，但并未提前30日通知，也未支付N+1补偿。孙丽华在公司工作近8年，主张：1）公司违法解除劳动合同，要求支付赔偿金2N（40万元）；2）支付未休年假折算工资5.8万元；3）补发年终奖8万元；4）支付加班费3.2万元。公司主张系合法裁员，仅同意支付N（20万元）作为经济补偿。案件已进入劳动仲裁阶段。',
    caseType: 'civil', opposingCounsel: '林立峰 法务（辉煌科技）', da: 45,
    categories: ['案件文书', '劳动合同', '工资证据', '加班证据', '公司文件'],
  })
  addTimeline(m6, [
    { type: 'milestone', title: '孙某被公司通知裁员', desc: '公司以组织架构调整为由要求当天交接离职', da: 75 },
    { type: 'note', title: '孙某到所咨询', desc: '咨询公司违法解除能否维权', da: 72 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '审查劳动合同、工资单、考勤记录', da: 68 },
    { type: 'milestone', title: '签订委托代理合同', desc: '委托代理劳动仲裁程序', da: 65 },
    { type: 'note', title: '向公司发送沟通函', desc: '要求依法支付赔偿金，公司拒绝', da: 60 },
    { type: 'file_upload', title: '收集证据材料', desc: '劳动合同、工资流水、考勤记录、年假记录', da: 55 },
    { type: 'note', title: '收集加班证据', desc: '导出企业微信加班记录、报销打车费记录', da: 50 },
    { type: 'milestone', title: '向仲裁委提交申请', desc: '提交仲裁申请书及证据副本', da: 45 },
    { type: 'milestone', title: '仲裁委受理', desc: '案号 京劳人仲字(2026)第1582号', da: 42 },
    { type: 'note', title: '公司提交答辩状', desc: '主张裁员合法，仅愿意支付20万补偿', da: 30 },
    { type: 'note', title: '证据交换', desc: '双方交换证据，我方提交29份证据', da: 25 },
    { type: 'note', title: '申请证人出庭', desc: '申请2名前同事证明公司未提前通知', da: 20 },
    { type: 'court_date', title: '仲裁庭开庭', desc: '预计一周后开庭', da: 10 },
  ])
  addFiles(m6, [
    ['仲裁申请书.docx','案件文书'], ['授权委托书.pdf','案件文书'],
    ['劳动合同.pdf','劳动合同'], ['员工手册.pdf','公司文件'], ['录用通知书.pdf','劳动合同'],
    ['工资银行流水.pdf','工资证据'], ['个人所得税纳税记录.pdf','工资证据'],
    ['考勤记录.pdf','加班证据'], ['加班审批记录.pdf','加班证据'], ['企业微信截图.pdf','加班证据'],
    ['年休假记录.pdf','工资证据'], ['年终奖制度.pdf','公司文件'],
    ['解除通知书.pdf','公司文件'], ['公司答辩状.pdf','对方提交'],
    ['赔偿计算表.xlsx','案件文书'],
  ])

  // ════════════════════════════════════════════
  // 7. 吴某诉恒大公司房屋买卖合同纠纷
  // ════════════════════════════════════════════
  const m7 = addMatter({
    title: '吴某等32户业主诉恒大地产房屋买卖合同纠纷（集体诉讼）',
    caseNumber: '(2026)京0108民初21037号', client: '吴建华等32户业主',
    counterparty: '恒大地产集团北京有限公司', practiceArea: '房产纠纷',
    stage: '证据收集', deadline: t(-14).toISOString(),
    courtName: '北京市海淀区人民法院', courtDate: undefined,
    description: '2022年，吴建华等32户业主分别与恒大地产签订《商品房预售合同》，购买海淀区"恒大华府"项目住房。合同约定2024年12月31日前交房。截至2026年，项目已停工超过18个月，仅完成主体结构封顶，装修、绿化、配套设施均未完成。开发商以资金链断裂为由多次延期。业主集体委托我所维权，拟诉请：1）要求开发商继续履行合同，限期交房并支付逾期交房违约金（按日万分之五）；2）或解除合同，返还已付购房款及利息并赔偿损失。目前正在收集证据，进行诉前财产保全。',
    caseType: 'civil', opposingCounsel: '恒大法务团队', da: 30,
    categories: ['购房合同', '付款证据', '沟通记录', '法律文书', '集体诉讼'],
  })
  addTimeline(m7, [
    { type: 'milestone', title: '32户业主集体到所咨询', desc: '业主代表吴建华等5人到所沟通维权方案', da: 60 },
    { type: 'milestone', title: '签订集体委托合同', desc: '32户业主全部签署授权委托书', da: 55 },
    { type: 'stage_change', title: '阶段变更: 待处理 → 审查中', desc: '逐一审查32份购房合同及付款凭证', da: 50 },
    { type: 'file_upload', title: '购房合同审查完成', desc: '发现合同均约定2024年12月底交房', da: 45 },
    { type: 'file_upload', title: '付款凭证整理', desc: '32户总计已付购房款约1.2亿元', da: 40 },
    { type: 'note', title: '实地查看项目现状', desc: '拍摄现场停工照片及视频', da: 38 },
    { type: 'note', title: '向住建委投诉', desc: '请求政府督促开发商复工', da: 35 },
    { type: 'milestone', title: '住建委回复', desc: '确认该项目监管账户资金已被挪用', da: 28 },
    { type: 'stage_change', title: '阶段变更: 审查中 → 证据收集', desc: '决定起诉并申请财产保全', da: 25 },
    { type: 'note', title: '调查恒大其他资产线索', desc: '查找恒大在京其他可执行财产', da: 20 },
    { type: 'note', title: '撰写诉前保全申请', desc: '申请查封恒大在京其他项目未售房产', da: 15 },
    { type: 'file_upload', title: '保全证据公证', desc: '对项目停工现状进行证据保全公证', da: 12 },
    { type: 'note', title: '推选诉讼代表人', desc: '32户业主推选吴建华等3人为诉讼代表人', da: 8 },
    { type: 'deadline', title: '计划本周提交起诉状及保全申请', desc: '争取在恒大转移资产前完成保全', da: 2 },
  ])
  addFiles(m7, [
    ['民事起诉状.docx','法律文书'], ['财产保全申请书.docx','法律文书'],
    ['购房合同（样本）.pdf','购房合同'], ['付款凭证汇总.xlsx','付款证据'],
    ['银行转账记录.pdf','付款证据'], ['贷款合同.pdf','付款证据'],
    ['项目停工照片.zip','沟通记录'], ['现场视频.mov','沟通记录'],
    ['律师函.pdf','法律文书'], ['授权委托书汇总.pdf','集体诉讼'],
    ['住建委回复函.pdf','沟通记录'], ['业主名单及金额.xlsx','集体诉讼'],
    ['公司法务回函.pdf','对方提交'], ['违约金计算表.xlsx','法律文书'],
    ['诉讼风险告知书.md','AI生成'],
  ])
}

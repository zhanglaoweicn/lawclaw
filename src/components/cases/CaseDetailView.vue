<template>
  <div class="case-detail-view">
    <div class="cdv-header">
      <el-button text @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon> 返回案件列表
      </el-button>
    </div>

    <div class="cdv-body">
      <!-- ═══ Left Column: Case info, timeline, files, sessions ═══ -->
      <div class="cdv-left">
        <!-- Case info header -->
        <div v-if="matter" class="cdv-info">
          <h2 class="cdv-title">{{ matter.title }}</h2>
          <div class="cdv-tags">
            <el-tag size="small" type="warning" effect="plain">{{ matter.practiceArea }}</el-tag>
            <!-- Stage as an inline-edit dropdown -->
            <el-dropdown @command="changeStage" trigger="click">
              <el-tag size="small" :type="stageTagType(matter.stage)" style="cursor:pointer">
                {{ matter.stage }}
                <el-icon style="margin-left:2px"><ArrowDown /></el-icon>
              </el-tag>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="s in allowedStages" :key="s"
                    :command="s"
                    :class="{ 'is-active': s === matter.stage }"
                  >
                    <span class="stage-dot" :style="{ background: stageColor(s) }"></span>
                    {{ s }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-tag v-if="matter.caseNumber" size="small" effect="plain" type="info">案号: {{ matter.caseNumber }}</el-tag>
          </div>

          <!-- Court countdown banner -->
          <div v-if="matter.courtDate" class="cdv-countdown" :class="countdownClass">
            <el-icon size="16"><AlarmClock /></el-icon>
            <span class="cdv-countdown-text">{{ countdownText }}</span>
            <span class="cdv-countdown-date">{{ formatDate(matter.courtDate) }} · {{ matter.courtName || '未知法院' }}</span>
          </div>

          <!-- 多期限列表 banner（替代旧单一 deadline banner） -->
          <!-- 注意：只要存在已撤销期限也必须渲染本块——否则撤销掉最后一个活跃期限后，
               「已撤销 N 项（点击查看/恢复）」入口随之消失，被撤销的期限再无 UI 恢复通道 -->
          <div v-if="activeDeadlines.length > 0 || revokedDeadlineCount > 0" class="cdv-deadlines">
            <div class="cdv-deadlines-header">
              <el-icon size="14"><AlarmClock /></el-icon>
              <span>期限跟踪（{{ activeDeadlines.length }} 项）</span>
              <button v-if="revokedDeadlineCount > 0" class="cdv-dl-revoked-hint"
                    title="查看已撤销期限，可恢复"
                    @click="showRevokedDialog = true">· 已撤销 {{ revokedDeadlineCount }} 项（点击查看/恢复）</button>
              <el-button text size="small" @click="openAddDeadline">
                <el-icon><Plus /></el-icon> 添加期限
              </el-button>
            </div>
            <div class="cdv-deadlines-list">
              <div v-for="dl in activeDeadlines" :key="dl.id"
                   class="cdv-deadline-item"
                   :class="`cdv-deadline-${deadlineUrgency(dl.date)}`">
                <div class="cdv-dl-left">
                  <el-tag size="small" effect="plain" :color="deadlineTypeColor(dl.type)" style="color:#fff;border:none">
                    {{ DEADLINE_TYPE_LABELS[dl.type] || dl.customLabel || '其他' }}
                  </el-tag>
                  <span class="cdv-dl-date">{{ formatDate(dl.date) }}</span>
                  <span class="cdv-dl-remain" :class="`cdv-dl-remain-${deadlineUrgency(dl.date)}`">
                    {{ formatDeadline(dl.date) }}
                  </span>
                </div>
                <div class="cdv-dl-right">
                  <span v-if="dl.note" class="cdv-dl-note">{{ dl.note }}</span>
                  <el-tag v-if="(dl.history?.length || 0) > 0" size="small" effect="plain"
                          class="cdv-dl-rev-tag" @click="openDeadlineHistory(dl)">
                    修订 {{ dl.history!.length }}
                  </el-tag>
                  <el-tooltip :content="dl.completed ? '标记为未完成' : '标记为已完成'" placement="top">
                    <el-button text size="small" @click="toggleDeadline(dl.id)">
                      <el-icon><CircleCheck v-if="dl.completed" /><CircleCheckFilled v-else /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="编辑此期限（旧版本自动留痕）" placement="top">
                    <el-button text size="small" @click="openEditDeadline(dl)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="撤销此期限（保留修订历史，可恢复）" placement="top">
                    <el-button text size="small" type="danger" @click="removeDeadline(dl.id)">
                      <el-icon><Close /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>
          <!-- 无期限时显示添加按钮 -->
          <div v-else-if="matter && !matter.stage.includes('已归档')" class="cdv-deadlines-empty">
            <el-button text size="small" @click="openAddDeadline">
              <el-icon><Plus /></el-icon> 添加期限跟踪
            </el-button>
          </div>

          <div class="cdv-meta">
            <div class="cdv-meta-item">
              <span class="cdv-meta-label">当事人</span>
              <span class="cdv-meta-val">{{ matter.client }}</span>
            </div>
            <div v-if="matter.clientRole" class="cdv-meta-item">
              <span class="cdv-meta-label">委托人角色</span>
              <span class="cdv-meta-val">
                <el-tag size="small" effect="plain">{{ CLIENT_ROLE_LABELS[matter.clientRole] || matter.clientRole }}</el-tag>
              </span>
            </div>
            <div v-if="matter.counterparty" class="cdv-meta-item">
              <span class="cdv-meta-label">相对方</span>
              <span class="cdv-meta-val">{{ matter.counterparty }}</span>
            </div>
            <div v-if="matter.opposingCounsel" class="cdv-meta-item">
              <span class="cdv-meta-label">对方律师</span>
              <span class="cdv-meta-val">{{ matter.opposingCounsel }}</span>
            </div>
            <div v-if="matter.caseCause" class="cdv-meta-item">
              <span class="cdv-meta-label">案由</span>
              <span class="cdv-meta-val">{{ matter.caseCause }}</span>
            </div>
            <div v-if="matter.procedureStage" class="cdv-meta-item">
              <span class="cdv-meta-label">审级</span>
              <span class="cdv-meta-val">
                <el-tag size="small" effect="plain" type="info">{{ PROCEDURE_STAGE_LABELS[matter.procedureStage] || matter.procedureStage }}</el-tag>
              </span>
            </div>
            <div v-if="matter.courtName" class="cdv-meta-item">
              <span class="cdv-meta-label">管辖法院</span>
              <span class="cdv-meta-val">{{ matter.courtName }}</span>
            </div>
            <div v-if="matter.filingDate" class="cdv-meta-item">
              <span class="cdv-meta-label">受理日期</span>
              <span class="cdv-meta-val">{{ formatDate(matter.filingDate) }}</span>
            </div>
            <div v-if="matter.claimAmount !== undefined" class="cdv-meta-item">
              <span class="cdv-meta-label">诉讼标的额</span>
              <span class="cdv-meta-val claim-amount">{{ formatCurrency(matter.claimAmount) }}</span>
            </div>
            <div v-if="matter.riskLevel" class="cdv-meta-item">
              <span class="cdv-meta-label">风险等级</span>
              <span class="cdv-meta-val">
                <el-tag size="small" :color="riskLevelColor(matter.riskLevel)" effect="dark">
                  {{ RISK_LEVEL_LABELS[matter.riskLevel] }}
                </el-tag>
              </span>
            </div>
          </div>

          <!-- 收费信息 -->
          <div v-if="matter.fee !== undefined || matter.feeType" class="cdv-fee-section">
            <span class="cdv-meta-label">律师费</span>
            <span class="cdv-fee-amount">{{ formatCurrency(matter.fee) }}</span>
            <el-tag v-if="matter.feeType" size="small" effect="plain" type="info" style="margin-left:8px">
              {{ FEE_TYPE_LABELS[matter.feeType] }}
            </el-tag>
          </div>

          <!-- 结案信息（仅已完成/已归档） -->
          <div v-if="matter.resolutionMethod || matter.judgmentResult" class="cdv-resolution-section">
            <div class="cdv-resolution-title">
              <el-icon size="14"><CircleCheckFilled /></el-icon>
              <span>结案信息</span>
            </div>
            <div v-if="matter.resolutionMethod" class="cdv-meta-item">
              <span class="cdv-meta-label">结案方式</span>
              <span class="cdv-meta-val">
                <el-tag size="small" type="success" effect="plain">
                  {{ RESOLUTION_METHOD_LABELS[matter.resolutionMethod] || matter.resolutionMethod }}
                </el-tag>
              </span>
            </div>
            <div v-if="matter.judgmentResult" class="cdv-meta-item cdv-judgment">
              <span class="cdv-meta-label">判决/调解结果</span>
              <p class="cdv-desc-text">{{ matter.judgmentResult }}</p>
            </div>
          </div>

          <!-- Edit button -->
          <div class="cdv-info-actions">
            <el-button size="small" text @click="showEditDialog = true">
              <el-icon><Edit /></el-icon> 编辑案件
            </el-button>
          </div>

          <div v-if="matter.description" class="cdv-desc-section">
            <span class="cdv-meta-label">案件描述</span>
            <p class="cdv-desc-text">{{ matter.description }}</p>
          </div>
        </div>

        <!-- Quick actions -->
        <div class="cdv-actions">
          <el-button type="primary" size="small" @click="openChat">
            <el-icon><ChatDotRound /></el-icon> AI 对话
          </el-button>
          <el-button size="small" @click="showTimeline = !showTimeline">
            <el-icon><Timer /></el-icon> {{ showTimeline ? '收起时间轴' : '时间轴' }}
          </el-button>
          <el-button v-if="matter?.courtDate && !hasCalendarEntry" size="small" @click="addCourtToCalendar">
            <el-icon><Calendar /></el-icon> 添加到日历
          </el-button>
        </div>

        <!-- 阶段推荐技能 -->
        <div v-if="recommendedSkills.length > 0" class="cdv-section cdv-recommend">
          <h3 class="section-title">
            <el-icon size="14"><MagicStick /></el-icon>
            推荐技能（当前阶段：{{ matter?.stage }}）
          </h3>
          <div class="recommend-list">
            <div v-for="s in recommendedSkills" :key="s.id" class="recommend-card" @click="invokeRecommendedSkill(s)">
              <span class="recommend-icon">{{ s.icon }}</span>
              <div class="recommend-body">
                <span class="recommend-name">{{ s.name }}</span>
                <span class="recommend-reason">{{ s.reason }}</span>
              </div>
              <el-icon class="recommend-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>

        <!-- Timeline section -->
        <transition name="page-fade">
          <div v-if="showTimeline" class="cdv-section">
            <h3 class="section-title">
              案件时间轴
              <el-button text size="small" type="primary" style="margin-left:8px" @click="openDecisionDialog">
                <el-icon><Edit /></el-icon> 记录决策
              </el-button>
            </h3>
            <div v-if="timelineEvents.length === 0" class="section-empty">
              <p>暂无时间轴记录</p>
              <p style="font-size:12px;margin-top:4px;opacity:0.6">案件操作（如阶段变更、文件上传）将自动记录在此处；「记录决策」可沉淀接案、调解、上诉等关键决策及理由</p>
            </div>
            <div v-else class="tl-list">
              <div v-for="ev in timelineEvents" :key="ev.id" class="tl-item">
                <div class="tl-dot" :class="'tl-dot-' + ev.type"></div>
                <div class="tl-line"></div>
                <div class="tl-content">
                  <div class="tl-title">
                    <el-tag v-if="ev.type === 'decision'" size="small" effect="dark" class="tl-decision-tag">⚖ 决策</el-tag>
                    {{ ev.title }}
                  </div>
                  <div v-if="ev.description" class="tl-desc">{{ ev.description }}</div>
                  <div class="tl-time">{{ formatDateTime(ev.createdAt) }}</div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- Related files section -->
        <div class="cdv-section">
          <h3 class="section-title">案件文件（{{ matterFiles.length }}）</h3>
          <div v-if="matterFiles.length === 0" class="section-empty">
            <p>暂无案件文件</p>
          </div>
          <div v-else class="file-group-list">
            <div v-for="(files, cat) in filesByCategory" :key="cat" class="file-group">
              <div class="file-group-title">{{ cat }}（{{ files.length }}）</div>
              <div class="file-group-items">
                <div v-for="f in files" :key="f.id" class="file-group-item"
                  :class="{ 'is-active': previewFile?.data === f.data }"
                  @click="openPreview(f)">
                  <el-icon size="14"><Document /></el-icon>
                  <span class="file-group-name">{{ f.name }}</span>
                  <span v-if="f.category === 'AI生成'" class="fgp-ai-tag">AI</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Related sessions section -->
        <div class="cdv-section">
          <h3 class="section-title">相关对话</h3>
          <div v-if="relatedSessions.length === 0" class="section-empty">
            <p>暂无相关对话</p>
            <el-button size="small" text type="primary" @click="openChat">开始新对话</el-button>
          </div>
          <div v-else>
            <div v-for="s in relatedSessions" :key="s.id" class="session-row" @click="openSession(s.id)">
              <div class="session-row-info">
                <div class="session-row-title">{{ s.title }}</div>
                <div class="session-row-meta">{{ s.messageCount }}轮对话</div>
              </div>
              <el-icon color="var(--legal-text-muted)"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Right Column: File preview / editor ═══ -->
      <div class="cdv-right" :class="{ 'has-preview': !!previewFile }">
        <div v-if="previewFile" class="cdv-preview">
          <div class="cdv-preview-header">
            <span class="cdv-preview-name">{{ previewFile.name }}</span>
            <div class="cdv-preview-actions">
              <template v-if="isEditableFile(previewFile.name)">
                <el-button v-if="!editor.editing" size="small" text @click="startEditing">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                <template v-else>
                  <el-button size="small" type="primary" @click="saveEdits" :loading="editor.saving">
                    <el-icon><Check /></el-icon> 保存
                  </el-button>
                  <el-button size="small" text @click="cancelEditing">
                    <el-icon><Close /></el-icon> 取消
                  </el-button>
                </template>
              </template>
              <el-button size="small" text @click="downloadPreviewFile">
                <el-icon><Download /></el-icon> 下载
              </el-button>
              <el-button size="small" text @click="previewFile = null">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="cdv-preview-body">
            <img v-if="editor.isImageFile(previewFile.name) && !editor.editing"
              :src="previewFile.data" class="cpp-image" alt="预览" />
            <div v-else-if="editor.isTextFile(previewFile.name) && editor.editing" class="cpp-editor">
              <textarea v-model="editTextInput" class="cpp-textarea" spellcheck="false"></textarea>
            </div>
            <div v-else-if="editor.isTextFile(previewFile.name)" class="cpp-markdown" v-html="renderedMarkdown"></div>
            <div v-else class="cpp-placeholder">
              <el-icon size="48"><Document /></el-icon>
              <p class="cpp-name">{{ previewFile.name }}</p>
              <p class="cpp-meta">{{ (previewFile.size / 1024).toFixed(1) }} KB</p>
            </div>
          </div>
        </div>
        <div v-else class="cdv-preview-empty">
          <el-icon size="36" color="var(--legal-text-muted)"><Document /></el-icon>
          <p>点击文件查看预览</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Edit Case Dialog -->
  <el-dialog v-model="showEditDialog" title="编辑案件" width="520px">
    <el-form label-position="top" v-if="matter">
      <el-form-item label="案件名称" required>
        <el-input v-model="editForm.title" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="当事人/客户">
            <el-input v-model="editForm.client" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="相对方">
            <el-input v-model="editForm.counterparty" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="案号">
            <el-input v-model="editForm.caseNumber" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="管辖法院">
            <el-input v-model="editForm.courtName" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="开庭日期">
            <el-date-picker v-model="editForm.courtDate" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="截止日期">
            <el-date-picker v-model="editForm.deadline" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="对方律师">
        <el-input v-model="editForm.opposingCounsel" />
      </el-form-item>
      <el-form-item label="案件描述">
        <el-input v-model="editForm.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showEditDialog = false">取消</el-button>
      <el-button type="primary" @click="confirmEdit">保存</el-button>
    </template>
  </el-dialog>

  <!-- 添加/编辑期限对话框（编辑模式：旧版本自动留痕到修订历史） -->
  <el-dialog v-model="showAddDeadlineDialog" :title="editingDeadlineId ? '编辑期限' : '添加期限跟踪'" width="520px" :close-on-click-modal="false">
    <el-form label-position="top" class="deadline-form">
      <el-form-item label="期限类型" required>
        <el-select v-model="newDeadline.type" placeholder="选择期限类型" style="width:100%" @change="onDeadlineTypeChange">
          <el-option v-for="t in DEADLINE_TYPES" :key="t.value" :label="t.label" :value="t.value">
            <span>{{ t.label }}</span>
            <span class="opt-meta">{{ t.desc }}</span>
          </el-option>
        </el-select>
        <div v-if="selectedDeadlineMeta" class="deadline-legal-hint">
          <span v-if="selectedDeadlineMeta.legalBasis">📚 {{ selectedDeadlineMeta.legalBasis }}</span>
          <span class="deadline-desc">{{ selectedDeadlineMeta.desc }}</span>
        </div>
      </el-form-item>
      <el-form-item v-if="newDeadline.type === 'custom'" label="自定义名称" required>
        <el-input v-model="newDeadline.customLabel" placeholder="如：申请执行和解期限" />
      </el-form-item>

      <!-- ── P1-3: 智能计算模式切换 ── -->
      <el-form-item label="计算模式">
        <el-radio-group v-model="deadlineCalcMode">
          <el-radio-button value="manual">手动指定日期</el-radio-button>
          <el-radio-button value="auto" :disabled="!isAutoCalcAvailable">智能计算（节假日顺延）</el-radio-button>
        </el-radio-group>
        <div v-if="!isAutoCalcAvailable && deadlineCalcMode === 'auto'" class="deadline-legal-hint">
          <span class="deadline-desc">该期限类型不支持自动计算，请手动指定</span>
        </div>
      </el-form-item>

      <el-form-item v-if="deadlineCalcMode === 'auto'" label="起始日（如送达日/收到日）" required>
        <el-date-picker v-model="newDeadline.startDate" type="date" placeholder="选择起始日期" style="width:100%" value-format="YYYY-MM-DD" />
      </el-form-item>

      <el-form-item v-if="deadlineCalcMode === 'auto' && isAutoCalcAvailable" label="法定天数">
        <el-input-number v-model="newDeadline.days" :min="1" :max="730" style="width:100%" />
        <div class="deadline-legal-hint">
          <span class="deadline-desc">默认值依据法律规定自动填充，可手动调整</span>
        </div>
      </el-form-item>

      <el-form-item v-if="deadlineCalcMode === 'auto'" label="">
        <el-button type="primary" plain size="small" @click="calcDeadlineWithHoliday" :loading="deadlineCalculating">
          <el-icon><MagicStick /></el-icon> 智能计算截止日
        </el-button>
        <div v-if="calcResult" class="calc-result" :class="{ 'calc-deferred': calcResult.deferred }">
          <div class="calc-result-main">
            <span class="calc-deadline">{{ calcResult.deadline }}</span>
            <span v-if="calcResult.deferred" class="calc-deferred-tag">已顺延</span>
          </div>
          <div v-if="calcResult.deferred" class="calc-original">原截止日：{{ calcResult.original_deadline }}（{{ calcResult.deferred_reason }}）</div>
          <div class="calc-meta">剩余 <strong :class="{ 'calc-overdue': (calcResult.days_remaining ?? 0) < 0 }">{{ calcResult.days_remaining }}</strong> 天 · {{ calcResult.law_basis }}</div>
        </div>
      </el-form-item>

      <el-form-item label="期限日期" required>
        <el-date-picker v-model="newDeadline.date" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="newDeadline.note" type="textarea" :rows="2" placeholder="如：自送达之日起算 / 举证期限内" />
      </el-form-item>
      <el-form-item v-if="editingDeadlineId" label="变更原因（写入修订历史，可留空）">
        <el-input v-model="deadlineChangeReason" placeholder="如：法院重新指定举证期限 / 当事人申请延期" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAddDeadlineDialog = false">取消</el-button>
      <el-button type="primary" @click="confirmAddDeadline" :disabled="!newDeadline.date || !newDeadline.type">
        {{ editingDeadlineId ? '保存（旧版本留痕）' : '添加' }}
      </el-button>
    </template>
  </el-dialog>

  <!-- 期限修订历史对话框（双时间线：每个旧版本都保留有效期窗口与变更原因） -->
  <el-dialog v-model="showDeadlineHistory" title="期限修订历史" width="560px">
    <template v-if="historyDeadline">
      <div class="dlh-current">
        <el-tag size="small" effect="plain" :color="deadlineTypeColor(historyDeadline.type)" style="color:#fff;border:none">
          {{ DEADLINE_TYPE_LABELS[historyDeadline.type] || historyDeadline.customLabel || '其他' }}
        </el-tag>
        <span class="dlh-current-date">{{ formatDate(historyDeadline.date) }}</span>
        <el-tag v-if="historyDeadline.supersededAt" type="danger" size="small" effect="plain">
          已撤销（{{ formatDateTime(new Date(historyDeadline.supersededAt)) }}）
        </el-tag>
        <el-tag v-else type="success" size="small" effect="plain">现行有效</el-tag>
        <el-button v-if="historyDeadline.supersededAt" size="small" type="primary" plain
                   style="margin-left:auto" @click="restoreRevokedDeadline">
          恢复此期限
        </el-button>
      </div>
      <el-alert v-if="!historyDeadline.history?.length" type="info" :closable="false"
                title="该期限从未被修改过，无历史版本。" style="margin-top:12px" />
      <el-timeline v-else style="margin-top:16px;padding-left:4px">
        <el-timeline-item v-for="(rev, i) in historyDeadline.history" :key="i"
                          :timestamp="`${formatDate(rev.validFrom)} → ${formatDate(rev.validUntil)}`"
                          placement="top" type="info">
          <div class="dlh-rev">
            <div class="dlh-rev-head">
              <el-tag size="small" effect="plain" :color="deadlineTypeColor(rev.type)" style="color:#fff;border:none">
                {{ DEADLINE_TYPE_LABELS[rev.type] || rev.customLabel || '其他' }}
              </el-tag>
              <span class="dlh-rev-date">{{ formatDate(rev.date) }}</span>
            </div>
            <div v-if="rev.note" class="dlh-rev-note">{{ rev.note }}</div>
            <div class="dlh-rev-reason">变更原因：{{ rev.changeReason || '（未填写）' }}</div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </template>
    <template #footer>
      <el-button @click="showDeadlineHistory = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 已撤销期限列表（软删除可恢复） -->
  <el-dialog v-model="showRevokedDialog" title="已撤销的期限" width="520px">
    <div v-if="revokedDeadlines.length === 0" class="section-empty"><p>没有已撤销的期限</p></div>
    <div v-else class="dlh-revoked-list">
      <div v-for="dl in revokedDeadlines" :key="dl.id" class="dlh-revoked-item">
        <el-tag size="small" effect="plain" :color="deadlineTypeColor(dl.type)" style="color:#fff;border:none">
          {{ DEADLINE_TYPE_LABELS[dl.type] || dl.customLabel || '其他' }}
        </el-tag>
        <span class="dlh-rev-date">{{ formatDate(dl.date) }}</span>
        <span class="dlh-rev-note">撤销于 {{ dl.supersededAt ? formatDateTime(new Date(dl.supersededAt)) : '' }}</span>
        <el-button size="small" type="primary" plain style="margin-left:auto" @click="restoreFromRevoked(dl)">
          恢复
        </el-button>
      </div>
    </div>
    <template #footer>
      <el-button @click="showRevokedDialog = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 记录决策对话框（律师决策沉淀为案件先例，借鉴 semantica Decision-as-first-class） -->
  <el-dialog v-model="showDecisionDialog" title="记录案件决策" width="560px" :close-on-click-modal="false">
    <el-form label-position="top">
      <el-form-item label="决策事项" required>
        <el-input v-model="decisionForm.title" placeholder="如：是否接受调解方案 / 是否提起上诉" />
      </el-form-item>
      <el-form-item label="考虑过的方案/选项">
        <el-input v-model="decisionForm.options" type="textarea" :rows="2"
                  placeholder="如：方案A 接受调解（折扣15%）；方案B 继续诉讼（胜诉率约60%，周期8个月）" />
      </el-form-item>
      <el-form-item label="决策结论" required>
        <el-input v-model="decisionForm.conclusion" type="textarea" :rows="2"
                  placeholder="最终选择及与对方的沟通安排" />
      </el-form-item>
      <el-form-item label="决策理由（风险评估/类案参考/当事人意愿）">
        <el-input v-model="decisionForm.reason" type="textarea" :rows="3"
                  placeholder="为什么选这个方案——这是未来同类案件最值得检索的内容" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showDecisionDialog = false">取消</el-button>
      <el-button type="primary" @click="confirmDecision" :disabled="!decisionForm.title || !decisionForm.conclusion">
        存入时间轴
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { watch } from 'vue'
import { ArrowLeft, ChatDotRound, Timer, Document, ArrowRight, Edit, Check, Close, Download, ArrowDown, AlarmClock, WarningFilled, Calendar, MagicStick, CircleCheckFilled, CircleCheck, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMatterStore } from '../../stores/matter'
import { useFileStore } from '../../stores/fileStore'
import { useFileEditor } from '../../composables/useFileEditor'
import { useChatStore } from '../../stores/chat'
import { useTimelineStore } from '../../stores/timeline'
import { useScheduleStore } from '../../stores/schedule'
import { backend } from '../../lib/backend'
import { renderMarkdown } from '../../lib/markdown'
import { dataUrlToText } from '../../lib/encoding'
import {
  stageColor, stageTagType, STAGE_TRANSITIONS,
  PROCEDURE_STAGE_LABELS, CLIENT_ROLE_LABELS, RISK_LEVEL_LABELS, RESOLUTION_METHOD_LABELS,
  FEE_TYPE_LABELS, riskLevelColor, formatCurrency,
  DEADLINE_TYPES, DEADLINE_TYPE_LABELS, deadlineTypeColor, deadlineUrgency, formatDeadline,
  getActiveDeadlines,
  type DeadlineUrgency,
} from '../../lib/caseConstants'
import type { DeadlineType, DeadlineItem } from '../../types/legal'

const props = defineProps<{
  matterId: string | null
}>()

const emit = defineEmits<{
  back: []
  'open-chat': [sessionId: string]
}>()

const matterStore = useMatterStore()
const fileStore = useFileStore()
const chatStore = useChatStore()
const timelineStore = useTimelineStore()
const scheduleStore = useScheduleStore()

const showTimeline = ref(true)
const previewFile = ref<{ name: string; data: string; size: number; type: string } | null>(null)
const showEditDialog = ref(false)

// ── 阶段推荐技能 ──
const recommendedSkills = ref<Array<{ id: string; name: string; icon: string; reason: string }>>([])

async function loadRecommendedSkills(stage: string) {
  if (!stage) { recommendedSkills.value = []; return }
  try {
    const result = await backend.recommendSkillsForStage(stage)
    recommendedSkills.value = result.recommended_skills || []
  } catch {
    recommendedSkills.value = []
  }
}

function invokeRecommendedSkill(skill: { id: string; name: string; icon: string }) {
  chatStore.newSession(props.matterId || undefined)
  chatStore.setPendingSkill({ id: skill.id, name: skill.name, icon: skill.icon, prompt: '' })
  emit('open-chat', chatStore.activeSessionId!)
}

const editor = useFileEditor(
  fileStore,
  () => ElMessage.success('文件已保存'),
  () => ElMessage.warning('保存失败'),
)

// 代理 editor.editText 以解决 v-model 对 Ref 的类型问题
const editTextInput = computed({
  get: () => editor.editText.value,
  set: (v: string) => { editor.editText.value = v },
})

// ── Computed ──
const timelineEvents = computed(() => {
  if (!props.matterId) return []
  return timelineStore.events.filter(e => e.matterId === props.matterId)
})

const matter = computed(() => {
  if (!props.matterId) return null
  return matterStore.matters.find(m => m.id === props.matterId) || null
})

/** 案件所有未完成期限（按日期升序） */
const activeDeadlines = computed<DeadlineItem[]>(() => {
  if (!matter.value?.deadlines) return []
  return matter.value.deadlines
    .filter(d => !d.supersededAt)   // 排除已撤销（软删除留痕）
    .slice()
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
})

/** 已撤销期限数（提示律师可追溯） */
const revokedDeadlineCount = computed(() =>
  (matter.value?.deadlines || []).filter(d => d.supersededAt).length
)

// ── 期限编辑（双模式：复用添加对话框）与修订历史 ──
const editingDeadlineId = ref<string | null>(null)
const deadlineChangeReason = ref('')
const showDeadlineHistory = ref(false)
const historyDeadlineId = ref<string | null>(null)

const historyDeadline = computed<DeadlineItem | null>(() => {
  if (!historyDeadlineId.value || !matter.value?.deadlines) return null
  return matter.value.deadlines.find(d => d.id === historyDeadlineId.value) || null
})

function openEditDeadline(dl: DeadlineItem) {
  editingDeadlineId.value = dl.id
  deadlineChangeReason.value = ''
  newDeadline.value = {
    type: dl.type,
    customLabel: dl.customLabel,
    date: dl.date.slice(0, 10),
    note: dl.note,
  }
  deadlineCalcMode.value = 'manual'
  showAddDeadlineDialog.value = true
}

// ── 已撤销期限（软删除恢复入口） ──
const showRevokedDialog = ref(false)
const revokedDeadlines = computed<DeadlineItem[]>(() =>
  (matter.value?.deadlines || []).filter(d => d.supersededAt)
)

function restoreFromRevoked(dl: DeadlineItem) {
  if (!props.matterId) return
  if (matterStore.restoreDeadline(props.matterId, dl.id)) {
    ElMessage.success('已恢复该期限，提醒与紧急列表将重新计入')
  } else {
    ElMessage.error('恢复失败')
  }
}

/** 打开添加对话框（重置编辑模式） */
function openAddDeadline() {
  editingDeadlineId.value = null
  deadlineChangeReason.value = ''
  newDeadline.value = { type: 'evidence', date: '', note: '' }
  deadlineCalcMode.value = 'manual'
  showAddDeadlineDialog.value = true
}

function openDeadlineHistory(dl: DeadlineItem) {
  historyDeadlineId.value = dl.id
  showDeadlineHistory.value = true
}

function restoreRevokedDeadline() {
  if (!props.matterId || !historyDeadline.value) return
  const id = historyDeadline.value.id
  if (matterStore.restoreDeadline(props.matterId, id)) {
    ElMessage.success('已恢复该期限（恢复动作计入修订历史）')
  } else {
    ElMessage.error('恢复失败')
  }
}

// ── 决策记录（借鉴 semantica Decision-as-first-class：决策+理由沉淀为可查先例） ──
const showDecisionDialog = ref(false)
const decisionForm = ref({ title: '', options: '', conclusion: '', reason: '' })

function openDecisionDialog() {
  decisionForm.value = { title: '', options: '', conclusion: '', reason: '' }
  showDecisionDialog.value = true
}

async function confirmDecision() {
  if (!props.matterId) return
  const { title, options, conclusion, reason } = decisionForm.value
  const descParts = [
    options ? `考虑过的方案：${options}` : '',
    `结论：${conclusion}`,
    reason ? `理由：${reason}` : '',
  ].filter(Boolean)
  try {
    await timelineStore.addEvent({
      matterId: props.matterId,
      type: 'decision',
      title,
      description: descParts.join('\n'),
      createdBy: 'user',
      metadata: { options, conclusion, reason },
    } as any)
    showDecisionDialog.value = false
    ElMessage.success('决策已存入时间轴')
  } catch {
    ElMessage.error('决策记录失败')
  }
}

// ── 添加期限对话框状态 ──
const showAddDeadlineDialog = ref(false)
const newDeadline = ref<{
  type: DeadlineType; customLabel?: string; date: string; note?: string
  startDate?: string; days?: number
}>({
  type: 'evidence', date: '', note: '',
})

const selectedDeadlineMeta = computed(() => {
  return DEADLINE_TYPES.find(t => t.value === newDeadline.value.type)
})

// ── P1-3: 智能期限计算引擎 ──
const deadlineCalcMode = ref<'manual' | 'auto'>('manual')
const deadlineCalculating = ref(false)
const calcResult = ref<{
  deadline?: string; original_deadline?: string; deferred?: boolean
  deferred_reason?: string; days_remaining?: number; law_basis?: string
} | null>(null)

// 期限类型 → 后端 calc_deadline 接受的 deadline_type 映射
const DEADLINE_TYPE_DAYS_MAP: Record<string, number> = {
  'filing': 7,
  'evidence': 15,
  'defense': 15,
  'appeal-judgment': 15,
  'appeal-ruling': 10,
  'appeal-criminal-judgment': 10,
  'appeal-criminal-ruling': 5,
  'enforcement': 730,
  'retrial': 180,
  'jurisdiction': 15,
  'appraisal': 30,
  'preservation': 30,
  'arbitration-sue': 15,
}

const isAutoCalcAvailable = computed(() => {
  return newDeadline.value.type !== 'custom' && newDeadline.value.type !== 'court-date'
    && newDeadline.value.type in DEADLINE_TYPE_DAYS_MAP
})

function onDeadlineTypeChange() {
  // 切换类型时清空自定义名称（仅 custom 类型保留）
  if (newDeadline.value.type !== 'custom') {
    newDeadline.value.customLabel = undefined
  }
  // 自动填充默认天数
  if (newDeadline.value.type in DEADLINE_TYPE_DAYS_MAP) {
    newDeadline.value.days = DEADLINE_TYPE_DAYS_MAP[newDeadline.value.type]
    deadlineCalcMode.value = 'auto'
  } else {
    deadlineCalcMode.value = 'manual'
  }
  // 重置计算结果
  calcResult.value = null
}

async function calcDeadlineWithHoliday() {
  if (!newDeadline.value.startDate || !newDeadline.value.days) {
    ElMessage.warning('请填写起始日和天数')
    return
  }
  deadlineCalculating.value = true
  try {
    const result = await backend.calcDeadline(
      newDeadline.value.startDate,
      newDeadline.value.days,
      newDeadline.value.type,
      true
    )
    if (result.error) {
      ElMessage.error(result.error)
    } else {
      calcResult.value = result
      // 自动填充到期限日期
      if (result.deadline) {
        newDeadline.value.date = result.deadline
      }
    }
  } catch (e) {
    ElMessage.error('计算失败：' + (e as Error).message)
  } finally {
    deadlineCalculating.value = false
  }
}

function confirmAddDeadline() {
  if (!props.matterId || !newDeadline.value.date || !newDeadline.value.type) return
  const matterId = props.matterId
  if (newDeadline.value.type === 'custom' && !newDeadline.value.customLabel) {
    ElMessage.warning('请填写自定义期限名称')
    return
  }
  const dateIso = new Date(newDeadline.value.date).toISOString()

  // ── 编辑模式：走双时间线更新（旧版本自动留痕） ──
  if (editingDeadlineId.value) {
    const ok = matterStore.updateDeadline(
      matterId, editingDeadlineId.value,
      {
        type: newDeadline.value.type,
        customLabel: newDeadline.value.customLabel,
        date: dateIso,
        note: newDeadline.value.note,
      },
      deadlineChangeReason.value || undefined,
    )
    if (ok) {
      ElMessage.success('期限已更新（旧版本已存入修订历史）')
      showAddDeadlineDialog.value = false
      editingDeadlineId.value = null
      deadlineChangeReason.value = ''
      newDeadline.value = { type: 'evidence', date: '', note: '' }
    } else {
      ElMessage.error('更新期限失败')
    }
    return
  }

  // ── 添加模式 ──
  const ok = matterStore.addDeadline(matterId, {
    type: newDeadline.value.type,
    customLabel: newDeadline.value.customLabel,
    date: dateIso,
    note: newDeadline.value.note,
    completed: false,
  })
  if (ok) {
    ElMessage.success(`已添加期限：${DEADLINE_TYPE_LABELS[newDeadline.value.type] || newDeadline.value.customLabel}`)
    showAddDeadlineDialog.value = false
    // 重置表单
    newDeadline.value = { type: 'evidence', date: '', note: '' }
  } else {
    ElMessage.error('添加期限失败')
  }
}

function toggleDeadline(deadlineId: string) {
  if (!props.matterId) return
  matterStore.toggleDeadline(props.matterId as string, deadlineId)
}

function removeDeadline(deadlineId: string) {
  if (!props.matterId) return
  const matterId = props.matterId
  ElMessageBox.confirm(
    '撤销后该期限不再提醒、不再计入紧急列表，但完整保留修订历史，可随时恢复。确定撤销？',
    '撤销期限（可恢复）',
    { confirmButtonText: '撤销', cancelButtonText: '取消', type: 'warning' },
  ).then(() => {
    matterStore.removeDeadline(matterId, deadlineId)
    ElMessage.success('已撤销期限（可在修订历史中恢复）')
  }).catch(() => {})
}

const matterFiles = computed(() => {
  if (!props.matterId) return []
  return fileStore.files.filter(f => f.matterId === props.matterId)
})

const filesByCategory = computed(() => {
  const groups: Record<string, typeof matterFiles.value> = {}
  for (const f of matterFiles.value) {
    if (!groups[f.category]) groups[f.category] = []
    groups[f.category].push(f)
  }
  return groups
})

const relatedSessions = computed(() => {
  if (!props.matterId) return []
  return chatStore.sessions
    .filter(s => s.matterId === props.matterId)
    .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
})

// ── Stage dropdown ──
const allowedStages = computed(() => {
  if (!matter.value) return []
  const transitions = STAGE_TRANSITIONS[matter.value.stage] || []
  return [matter.value.stage, ...transitions]  // current stage + all allowed next
})

function changeStage(newStage: string) {
  if (!props.matterId || !matter.value || newStage === matter.value.stage) return
  matterStore.updateMatter(props.matterId, { stage: newStage as any })
  ElMessage.success(`阶段已变更为「${newStage}」`)
}

// ── Court countdown ──
const countdownClass = computed(() => {
  if (!matter.value?.courtDate) return ''
  const diff = new Date(matter.value.courtDate).getTime() - Date.now()
  if (diff < 0) return 'cdv-countdown-past'
  if (diff < 7 * 86400000) return 'cdv-countdown-soon'
  return ''
})

const countdownText = computed(() => {
  if (!matter.value?.courtDate) return ''
  const diff = new Date(matter.value.courtDate).getTime() - Date.now()
  if (diff < 0) return `开庭已过 ${Math.ceil(Math.abs(diff) / 86400000)} 天`
  // 按自然日计算：今天=0，明天=1（ceil 会把"明天上午"算成"今天"）
  const target = new Date(matter.value.courtDate)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const targetDay = new Date(target.getFullYear(), target.getMonth(), target.getDate())
  const days = Math.round((targetDay.getTime() - today.getTime()) / 86400000)
  if (days === 0) return '今天开庭！'
  return `${days} 天后开庭`
})

// ── Calendar sync ──
const hasCalendarEntry = computed(() => {
  if (!props.matterId) return true
  return scheduleStore.sortedItems.some(i => i.id === `court-${props.matterId}`)
})

function addCourtToCalendar() {
  if (!props.matterId || !matter.value?.courtDate) return
  // 按 court-{matterId} 规范键 upsert（与 syncFromMatters 同键，避免出现重复开庭日程）
  const created = scheduleStore.ensureCourtItem(
    props.matterId,
    matter.value.title,
    matter.value.courtDate,
    matter.value.courtName || '',
  )
  if (created) {
    ElMessage.success('已添加到日历')
  } else {
    ElMessage.info('该开庭已存在于日历中')
  }
}

// ── Markdown rendering（统一经 lib/markdown 的 DOMPurify 消毒出口） ──
const renderedMarkdown = computed(() => {
  if (!previewFile.value || !editor.isTextFile(previewFile.value.name)) return ''
  return renderMarkdown(dataUrlToText(previewFile.value.data))
})

// ── Helpers ──
function isEditableFile(name: string) { return editor.isTextFile(name) }

function formatDateTime(d: Date) {
  const date = new Date(d)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(d: string | Date) {
  return new Date(d).toLocaleDateString('zh-CN')
}

// ── File preview ──
function openPreview(f: { name: string; data: string; size: number; type: string }) {
  previewFile.value = f
  editor.editing.value = false
}

function downloadPreviewFile() {
  if (!previewFile.value) return
  const a = document.createElement('a')
  a.href = previewFile.value.data
  a.download = previewFile.value.name
  a.click()
}

// ── Inline editing ──
function startEditing() {
  if (previewFile.value) editor.startEditing(previewFile.value)
}

function cancelEditing() {
  editor.cancelEditing()
}

async function saveEdits() {
  await editor.saveEdits(previewFile)
}

// ── Load timeline on mount ──
watch(() => props.matterId, (id) => {
  if (id) timelineStore.loadEventsForMatter(id)
}, { immediate: true })

// ── 阶段变化时自动加载推荐技能 ──
watch(() => matter.value?.stage, (newStage) => {
  if (newStage) loadRecommendedSkills(newStage)
}, { immediate: true })

function openChat() {
  if (!props.matterId) return
  const session = chatStore.findOrCreateSessionForMatter(props.matterId)

  // Write session event to timeline
  if (session) {
    import('../../stores/timeline').then(({ useTimelineStore }) => {
      useTimelineStore().addSessionEvent(props.matterId!, session.title)
    })
  }

  emit('open-chat', chatStore.activeSessionId || '')
}

function openSession(id: string) {
  chatStore.switchSession(id)
  // Navigate to assistant — emit open-chat so App.vue switches view
  emit('open-chat', id)
}

// ── Edit dialog integration ──
const editForm = ref({
  title: '', client: '', counterparty: '', caseNumber: '', courtName: '',
  courtDate: '', deadline: '', opposingCounsel: '', description: '',
})

/** 编辑对话框"截止日期"对应的期限：最近的非开庭类现行期限（deadlines[] 模型） */
function nearestEditableDeadline(matterId: string | null): DeadlineItem | null {
  if (!matterId) return null
  const m = matterStore.matters.find(x => x.id === matterId)
  return getActiveDeadlines(m?.deadlines).find(d => d.type !== 'court-date') || null
}

watch(() => showEditDialog.value, (v) => {
  if (v && matter.value) {
    const nearestDl = nearestEditableDeadline(props.matterId)
    editForm.value = {
      title: matter.value.title,
      client: matter.value.client,
      counterparty: matter.value.counterparty || '',
      caseNumber: matter.value.caseNumber || '',
      courtName: matter.value.courtName || '',
      courtDate: matter.value.courtDate || '',
      deadline: nearestDl ? nearestDl.date.slice(0, 10) : '',
      opposingCounsel: matter.value.opposingCounsel || '',
      description: matter.value.description || '',
    }
  }
})

function confirmEdit() {
  if (!props.matterId || !matter.value) return
  const f = editForm.value
  matterStore.updateMatter(props.matterId, {
    title: f.title,
    client: f.client,
    counterparty: f.counterparty || undefined,
    caseNumber: f.caseNumber || undefined,
    courtName: f.courtName || undefined,
    courtDate: f.courtDate || undefined,
    opposingCounsel: f.opposingCounsel || undefined,
    description: f.description || undefined,
  })
  // 截止日期走 deadlines[]（多期限模型）：变更写修订历史，无期限则新建
  if (f.deadline) {
    const nearestDl = nearestEditableDeadline(props.matterId)
    const dateIso = new Date(f.deadline).toISOString()
    if (nearestDl && nearestDl.date.slice(0, 10) !== f.deadline) {
      matterStore.updateDeadline(props.matterId, nearestDl.id, { date: dateIso }, '编辑案件对话框修改')
    } else if (!nearestDl) {
      matterStore.addDeadline(props.matterId, {
        type: 'evidence', date: dateIso, note: '编辑案件时添加', completed: false,
      })
    }
  }
  showEditDialog.value = false
  ElMessage.success('案件已更新')
}
</script>

<style scoped>
.case-detail-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  overflow: hidden;
}

.cdv-header { margin-bottom: 12px; flex-shrink: 0; }

/* ── Two-column body ── */
.cdv-body {
  flex: 1;
  display: flex;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.cdv-left {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
  padding-right: 4px;
}

.cdv-right {
  width: 0;
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.2s ease;
}

.cdv-right.has-preview {
  width: 420px;
  border-left: 1px solid var(--el-border-color-lighter);
  padding-left: 16px;
}

/* ── Right panel: preview ── */
.cdv-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.cdv-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 12px;
  flex-shrink: 0;
}

.cdv-preview-name {
  font-size: 13px;
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.cdv-preview-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 8px;
}

.cdv-preview-body {
  flex: 1;
  overflow-y: auto;
}

.cdv-preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--legal-text-muted);
  font-size: 13px;
  gap: 12px;
}

.cpp-image { max-width: 100%; object-fit: contain; border-radius: var(--radius-sm); }

.cpp-editor { height: 100%; }

.cpp-textarea {
  width: 100%;
  height: 100%;
  min-height: 300px;
  border: 1px solid var(--el-border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.7;
  resize: none;
  background: var(--legal-bg-card);
  color: var(--legal-text);
  outline: none;
}

.cpp-textarea:focus { border-color: var(--legal-navy); box-shadow: 0 0 0 1px var(--legal-navy) inset; }

.cpp-markdown {
  height: 100%;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
}

.cpp-markdown :deep(h2) { font-size: 18px; margin: 0 0 12px; color: var(--legal-navy); }
.cpp-markdown :deep(p) { margin: 0 0 8px; }
.cpp-markdown :deep(ul), .cpp-markdown :deep(ol) { padding-left: 20px; margin: 4px 0; }
.cpp-markdown :deep(code) { background: var(--el-fill-color); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.cpp-markdown :deep(blockquote) { border-left: 3px solid var(--legal-gold); margin: 8px 0; padding: 4px 12px; color: var(--legal-text-secondary); background: var(--el-fill-color-lighter); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
.cpp-markdown :deep(th) { background: var(--el-fill-color); font-weight: 600; }

.cpp-placeholder { text-align: center; color: var(--legal-text-muted); padding: 40px 0; }
.cpp-name { font-size: 15px; font-weight: 600; color: var(--legal-text); margin: 12px 0 4px; }
.cpp-meta { font-size: 13px; }

/* ── Case info ── */
.cdv-info {
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 12px;
}

/* ── 期限智能计算结果 ── */
.calc-result {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-sm);
  font-size: 12px;
}
.calc-result.calc-deferred {
  background: rgba(230, 162, 60, 0.08);
  border-color: rgba(230, 162, 60, 0.3);
}
.calc-result-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.calc-deadline {
  font-size: 16px;
  font-weight: 600;
  color: var(--legal-navy);
}
.calc-deferred-tag {
  display: inline-block;
  padding: 1px 6px;
  background: #e6a23c;
  color: #fff;
  border-radius: 4px;
  font-size: 10px;
}
.calc-original {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  margin-bottom: 4px;
}
.calc-meta {
  color: var(--el-text-color-regular);
  font-size: 11px;
}
.calc-overdue {
  color: #f56c6c;
}

.cdv-title { margin: 0 0 8px; font-size: 18px; color: var(--legal-navy); }

.cdv-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }

.cdv-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 20px; }
.cdv-desc { grid-column: 1 / -1; }

.cdv-meta-item { display: flex; flex-direction: column; gap: 1px; }
.cdv-meta-label { font-size: 11px; color: var(--legal-text-muted); letter-spacing: 0.5px; }
.cdv-meta-val { font-size: 13px; color: var(--legal-text); }

/* 标的额强调显示 */
.cdv-meta-val.claim-amount {
  font-size: 14px;
  font-weight: 600;
  color: var(--legal-gold-dark);
  font-family: var(--font-heading);
}

/* 收费信息区块 */
.cdv-fee-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--legal-gold);
}
.cdv-fee-amount {
  font-size: 15px;
  font-weight: 600;
  color: var(--legal-gold-dark);
  font-family: var(--font-heading);
}

/* 结案信息区块 */
.cdv-resolution-section {
  margin-top: 10px;
  padding: 10px 12px;
  background: rgba(45, 125, 78, 0.05);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--el-color-success);
}
.cdv-resolution-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-success);
  margin-bottom: 6px;
}
.cdv-judgment {
  grid-column: 1 / -1;
  margin-top: 4px;
}
.cdv-judgment .cdv-desc-text {
  margin: 4px 0 0;
  padding: 6px 8px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.cdv-actions { display: flex; gap: 8px; margin-bottom: 12px; }

/* ── 阶段推荐技能 ── */
.cdv-recommend .section-title {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--legal-gold-dark);
}
.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.recommend-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--legal-gold-bg, rgba(212,168,67,0.06));
  border: 1px solid var(--legal-gold-lighter, rgba(212,168,67,0.15));
  cursor: pointer;
  transition: all 0.15s;
}
.recommend-card:hover {
  border-color: var(--legal-gold);
  transform: translateX(2px);
}
.recommend-icon { font-size: 20px; flex-shrink: 0; }
.recommend-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.recommend-name { font-size: 13px; font-weight: 600; color: var(--legal-navy); }
.recommend-reason { font-size: 11px; color: var(--legal-text-muted); }
.recommend-arrow { color: var(--legal-text-muted); flex-shrink: 0; }

/* ── Info actions ── */
.cdv-info-actions { margin-top: 8px; }

/* ── Countdown banner ── */
.cdv-countdown {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  margin: 10px 0;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
}
.cdv-countdown-soon {
  background: var(--legal-warning-bg);
  border-color: var(--legal-warning);
  color: var(--legal-warning);
}
.cdv-countdown-past {
  background: var(--legal-danger-bg);
  border-color: var(--legal-danger);
  color: var(--legal-danger);
}
.cdv-countdown-text { font-weight: 600; font-size: 14px; }
.cdv-countdown-date { font-size: 12px; opacity: 0.7; margin-left: auto; }

/* ── 多期限列表 ── */
.cdv-deadlines {
  margin: 8px 0;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-md);
  border: 1px solid var(--el-border-color-extra-light);
}
.cdv-deadlines-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--legal-navy);
  margin-bottom: 8px;
}
.cdv-deadlines-header .el-button { margin-left: auto; }
.cdv-deadlines-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cdv-deadline-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: var(--el-bg-color);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--el-border-color);
  font-size: 12px;
}
.cdv-deadline-overdue { border-left-color: var(--el-color-danger); background: rgba(245,108,108,0.04); }
.cdv-deadline-critical { border-left-color: var(--el-color-danger); }
.cdv-deadline-warning { border-left-color: var(--el-color-warning); }
.cdv-deadline-soon { border-left-color: var(--legal-gold); }
.cdv-deadline-normal { border-left-color: var(--el-color-success); }

.cdv-dl-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cdv-dl-date {
  font-weight: 500;
  color: var(--legal-text);
}
.cdv-dl-remain {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 600;
}
.cdv-dl-remain-overdue { background: rgba(245,108,108,0.15); color: var(--el-color-danger); }
.cdv-dl-remain-critical { background: rgba(245,108,108,0.1); color: var(--el-color-danger); }
.cdv-dl-remain-warning { background: rgba(230,162,60,0.1); color: var(--el-color-warning); }
.cdv-dl-remain-soon { background: rgba(184,151,62,0.08); color: var(--legal-gold-dark); }
.cdv-dl-remain-normal { background: rgba(103,194,58,0.08); color: var(--el-color-success); }

.cdv-dl-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.cdv-dl-note {
  font-size: 11px;
  color: var(--legal-text-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* ── 双时间线：修订徽章 + 修订历史对话框 ── */
.dlh-revoked-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; margin-bottom: 6px;
  background: var(--legal-navy-bg); border-radius: var(--radius-sm);
}
.cdv-dl-revoked-hint { font-size: 11px; color: var(--legal-text-muted); font-weight: 400; background: none; border: none; cursor: pointer; padding: 0; }
.cdv-dl-revoked-hint:hover { color: var(--legal-gold); text-decoration: underline; }
.cdv-dl-rev-tag {
  cursor: pointer;
  border: 1px dashed var(--legal-gold) !important;
  color: var(--legal-gold) !important;
  background: transparent !important;
}
.cdv-dl-rev-tag:hover { background: var(--legal-navy-bg) !important; }
.dlh-current {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: var(--legal-navy-bg);
  border-radius: var(--radius-sm);
}
.dlh-current-date { font-weight: 600; font-size: 14px; color: var(--legal-text); }
.dlh-rev-head { display: flex; align-items: center; gap: 8px; }
.dlh-rev-date { font-weight: 600; font-size: 13px; color: var(--legal-text); }
.dlh-rev-note { font-size: 12px; color: var(--legal-text-secondary); margin-top: 4px; }
.dlh-rev-reason { font-size: 11px; color: var(--legal-text-muted); margin-top: 4px; }
/* ── 决策记录 ── */
.tl-decision-tag { margin-right: 6px; background: var(--legal-gold) !important; border: none; color: #1a2744 !important; }

.cdv-deadlines-empty {
  margin: 8px 0;
  padding: 8px 12px;
  text-align: center;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-md);
  border: 1px dashed var(--el-border-color);
}

/* ── 添加期限对话框 ── */
.deadline-form { padding: 0 4px; }
.opt-meta {
  float: right;
  color: var(--legal-text-muted);
  font-size: 11px;
  max-width: 240px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.deadline-legal-hint {
  margin-top: 4px;
  padding: 6px 8px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--legal-text-secondary);
  line-height: 1.5;
}
.deadline-legal-hint span:first-child {
  color: var(--legal-navy);
  font-weight: 600;
  margin-right: 6px;
}
.deadline-desc { display: block; margin-top: 2px; }

/* ── Description section ── */
.cdv-desc-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.cdv-desc-text {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--legal-text-secondary);
  line-height: 1.6;
}

/* ── Stage dot in dropdown ── */
.stage-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

/* ── Sections ── */
.cdv-section {
  background: var(--legal-bg-card);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 12px;
}

.section-title { margin: 0 0 10px; font-size: 14px; color: var(--legal-navy); }
.section-empty { text-align: center; padding: 16px 0; color: var(--legal-text-muted); font-size: 13px; }

/* ── File groups ── */
.file-group-list { display: flex; flex-direction: column; gap: 8px; }

.file-group-title { font-size: 12px; font-weight: var(--weight-semibold); color: var(--legal-text-secondary); margin-bottom: 4px; }

.file-group-items { display: flex; flex-wrap: wrap; gap: 4px; }

.file-group-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: background var(--transition-fast);
  border: 1px solid transparent;
}

.file-group-item:hover { background: var(--el-fill-color-light); }
.file-group-item.is-active { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-7); }

.fgp-ai-tag {
  font-size: 9px;
  background: var(--legal-gold-bg);
  color: var(--legal-gold-dark);
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  margin-left: 2px;
}

.file-group-name { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Sessions ── */
.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  cursor: pointer;
}
.session-row:last-child { border-bottom: none; }
.session-row:hover { background: var(--el-fill-color-light); margin: 0 -8px; padding: 8px; border-radius: var(--radius-sm); }
.session-row-info { flex: 1; min-width: 0; }
.session-row-title { font-size: 13px; font-weight: var(--weight-medium); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-row-meta { font-size: 12px; color: var(--legal-text-muted); margin-top: 2px; }

/* ── Timeline ── */
.tl-list { position: relative; padding-left: 20px; }
.tl-item { position: relative; padding-bottom: 16px; padding-left: 16px; }
.tl-item:last-child { padding-bottom: 0; }
.tl-item:last-child .tl-line { display: none; }
.tl-dot {
  position: absolute; left: -20px; top: 4px; width: 10px; height: 10px; border-radius: 50%; z-index: 1;
  border: 2px solid var(--el-border-color); background: var(--legal-bg-card);
}
.tl-dot-milestone { border-color: var(--legal-success); background: var(--legal-success-bg); }
.tl-dot-stage_change { border-color: var(--legal-gold); background: var(--legal-gold-bg); }
.tl-dot-file_upload { border-color: var(--legal-info); background: var(--legal-info-bg); }
.tl-dot-court_date { border-color: var(--legal-danger); background: var(--legal-danger-bg); }
.tl-dot-session { border-color: var(--legal-navy); background: var(--legal-navy-bg); }
.tl-dot-deadline { border-color: var(--legal-danger); background: var(--legal-danger-bg); }
.tl-dot-note { border-color: var(--legal-info); background: var(--legal-info-bg); }
.tl-dot-decision { border-color: var(--legal-gold); background: var(--legal-gold-bg); box-shadow: 0 0 0 3px var(--legal-gold-bg); }
.tl-line { position: absolute; left: -16px; top: 14px; bottom: 0; width: 1px; background: var(--el-border-color-lighter); }
.tl-content { font-size: 13px; }
.tl-title { font-weight: var(--weight-medium); color: var(--legal-text); margin-bottom: 2px; }
.tl-desc { font-size: 12px; color: var(--legal-text-secondary); margin-bottom: 2px; }
.tl-time { font-size: 11px; color: var(--legal-text-muted); }

/* ── Dark mode ── */
[data-theme="dark"] .cdv-countdown {
  background: rgba(61,90,128,0.3);
  border-color: var(--legal-navy);
}
[data-theme="dark"] .cdv-countdown-soon {
  background: var(--legal-warning-bg);
  border-color: var(--legal-warning);
}
[data-theme="dark"] .cdv-countdown-past {
  background: var(--legal-danger-bg);
  border-color: var(--legal-danger);
}
[data-theme="dark"] .cdv-deadline-soon {
  background: var(--legal-warning-bg);
  border-color: var(--legal-warning);
}
[data-theme="dark"] .cdv-deadline-overdue {
  background: var(--legal-danger-bg);
  border-color: var(--legal-danger);
}
</style>

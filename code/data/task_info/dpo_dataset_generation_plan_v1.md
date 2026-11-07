# 招聘实体抽取与分类 DPO 数据集生成计划 v1.1

> 状态：计划稿，仅定义生成、审核、分阶段训练与验收方案；本文不包含任何 DPO 样本。  
> 目标提示词：`recruitment_label_prompts_v2`  
> 建议首轮规模：10,000 条验收合格的偏好对  
> 基本单元：同一业务提示下的 `chosen` 与 `rejected`，且二者形成明确、可解释、贴近模型真实错误的偏好差异。

> v1.1 口径：SFT 数据只提供原始输入语料，不提供本轮 DPO 的答案标签。chosen 和合成 rejected 均由大模型依据项目提示词与锁定候选体系独立生成；职位分类候选唯一取自根目录 `job_cate.json`，其余分类任务候选唯一取自 `label_prompts_v2.md` 对应任务。

## 1. 项目依据与当前基线

### 1.1 约束来源

1. 任务定义、任务提示词、输出 schema 和抽取规则以 `code/data/task_info/label_prompts_v2.md` 为准。
2. `job_name_classification`、`taxonomy_leaf_to_parent`、`taxonomy_level2_to_children` 的合法职位树唯一取自根目录 `job_cate.json`；不得根据提示词旧副本、SFT 旧标签或模型常识增加、删除、改名或移动任何类别。
3. `work_type_classification`、`workplace_classification`、`settlement_classification`、`work_time_classification`、`benefit_classification` 的合法候选唯一取自 `label_prompts_v2.md` 各任务提示词中的“候选分类体系”。
4. 业务文本形态与语义来源优先使用 `code/data/gemini_labeled_v2/tasks_fixed/*/train.jsonl` 中已进入 SFT 的 9 类任务输入；读取时只向生成模型提供 system/instruction 与 input，不提供现有 output。
5. 可追溯原始语料来自 `code/data/processed/job_posts_clean.jsonl` 和 `code/data/processed/search_queries_clean.jsonl`；未经证明进入当前 `tasks_fixed` 的脏数据不得直接进入生成池。
6. 本轮 chosen 不复用 SFT 既有标签。大模型必须基于原始输入、任务提示词和权威候选独立重新标注；SFT 旧 output 只允许在生成完成后的盲审统计中比较，不能作为生成上下文或答案来源。
7. 既有 taxonomy 数据可用于校验 `job_cate.json` 的解析逻辑，但最终类别与路径仍以 `job_cate.json` 为准。
8. 冻结测试集、quick 30%、holdout 70% 及其近重复簇全部隔离，不参与样本生成、筛选阈值调优或人工规则归纳。
9. 现有 DPO v1-v7 只用于评估回归风险和归纳错误类型，不作为本轮 chosen/rejected 的语义答案来源。

### 1.2 大模型独立重标注原则

本轮所谓“基于 SFT 语料生成 DPO”专指：使用 SFT 的原始输入作为信息来源，由大模型重新生成标签，而不是从 SFT 的 `output` 字段复制 chosen。

1. 生成模型输入仅包含：任务 system prompt、原始业务 input、该任务权威候选快照，以及本轮要求的目标错误类型。
2. 对实体抽取，由大模型按 16 字段规则独立生成 chosen；除 `position[1]` 和标准化 `workMode` 外，非空内容必须逐字来自输入。
3. 对职位分类，由大模型在 `job_cate.json` 的 26 个一级类、155 个二级类、1,058 条三级路径内独立选择；任何文件外路径直接拒收。
4. 对其余分类任务，由大模型在对应提示词候选集合内独立选择；任何候选外类别直接拒收。
5. 对两个 taxonomy 任务，输出仍由大模型生成，但必须通过 `job_cate.json` 的确定性父子关系校验；校验失败即丢弃，不使用校验器静默篡改模型答案。
6. rejected 由大模型按本计划列举的错误类型和比例生成；可以参考模型真实错误模式，但不能复制既有 DPO 答案。
7. 生成与审核隔离：审核模型只看到原始输入、候选集合及匿名化的 A/B 输出，不看到 SFT 旧标签，也不知道哪一项是预设 chosen。

候选体系在 Stage 0 固化为以下只读快照：

| 任务 | 唯一候选来源 | 锁定规模/规则 |
| --- | --- | --- |
| `entity_extraction` | `label_prompts_v2.md` | 固定 16 字段 schema；不是分类闭集 |
| `job_name_classification` | `job_cate.json` | 26 个一级类、155 个二级类、1,058 条三级路径 |
| `taxonomy_leaf_to_parent` | `job_cate.json` | 1,058 条路径包含 848 个不同三级名称，其中 653 个名称只属于一条路径、可直接判断；195 个跨路径重名名称不得作为唯一父类输入 |
| `taxonomy_level2_to_children` | `job_cate.json` | 155 个一级/二级完整路径及其原始 children 列表 |
| `work_type_classification` | 对应任务提示词 | 9 类 |
| `workplace_classification` | 对应任务提示词 | 147 条标准一级-二级路径；一级闭集，二级按提示词规则允许原实体回退 |
| `settlement_classification` | 对应任务提示词 | 7 类 |
| `work_time_classification` | 对应任务提示词 | 29 类（含“其他”） |
| `benefit_classification` | 对应任务提示词 | 43 类 |

### 1.3 SFT 数据现状

当前 `recruitment_label_prompts_v2` 概览共 93,765 条、9 个业务任务：

| 任务 | SFT 样本数 | DPO 规划判断 |
| --- | ---: | --- |
| `entity_extraction` | 39,975 | 重点解决边界、跨字段混淆、简洁性与信息保留 |
| `job_name_classification` | 34,511 | 重点解决三级路径混淆与上下文消歧 |
| `benefit_classification` | 10,683（清理后训练文件 10,173） | 重点解决“其他”过用和语义扩大 |
| `work_time_classification` | 4,018 | 重点解决相邻班制混淆和“其他”过用 |
| `workplace_classification` | 3,232（另有 cleaned 版本） | 重点解决一级功能类和二级回退规则 |
| `taxonomy_leaf_to_parent` | 653 | 作为分类树一致性锚点，不做无意义随机错配 |
| `work_type_classification` | 275 | 小类全覆盖，强化低频类别 |
| `settlement_classification` | 263 | 小类全覆盖，强化薪资单位与结算方式的区别 |
| `taxonomy_level2_to_children` | 155 | 覆盖全部二级路径，重点做漏项/多项困难负例 |

实体抽取共有 16 个字段。现有 SFT 冻结集 quick 30% 评测中，JSON Parse 为 99.86%、Schema Exact 为 99.86%，但 `responsibilities` 精确率为 61.50%、`requirements` 为 63.67%，岗位分类 `level3` 为 75.73%，工作时间 `fullCategory` 为 69.64%。因此新 DPO 的主要收益目标是业务规则偏好，而不是重复教授基础 JSON。

既有 v6 DPO quick 30% 曾出现 JSON Parse 从 99.86% 降到 98.34%、岗位分类 Object Exact 从 66.47% 降到 37.23% 的明显回退。新方案必须采用小批量阶段训练和全局回归门禁，不能把大量合成对一次性并入。

## 2. DPO 调优目标与非目标

### 2.1 核心目标

1. **边界与简洁性**：抽取结果是原文中的最短充分表达，去掉句式冗余，但保留能区分实体/要求/职责的关键限定词。
2. **类别准确性**：分类结果严格属于项目合法类别，并优先解决真实相邻类别、父子路径和上下文歧义。
3. **幻觉控制**：除 `position[1]` 与标准化 `workMode` 外，抽取内容必须逐字可回指原文；分类不得创造候选外标签。
4. **召回保持**：简洁不能以遗漏关键对象、动作、技术、行业、资历、数量、否定词或范围限定为代价。
5. **结构稳定**：所有输出保持对应任务唯一 schema，不增加解释、Markdown、额外层级或别名字段。

### 2.2 非目标

- 不复制、改写或轻度扰动 SFT 旧 output 作为 chosen；chosen 必须由大模型对原始输入重新标注。
- 不用与业务无关的随机文本充当 rejected。
- 不通过缩短所有字段来追求表面“简洁”。
- 不把抽取任务和标准分类任务混为一个输出。
- 不用 frozen test 的答案、预测输出或其错误分析反向生成训练样本。
- 不为了配额把可判断样本错误标为“其他”，也不把无法判断的样本强行归入具体类。

## 3. 统一错误类型体系

每条偏好对只设一个 `primary_error_type`，可附加多个次级标签。chosen 与 rejected 原则上只发生一个主要语义错误，避免模型无法判断偏好来自哪一处。

| 错误代码 | 错误类型 | rejected 模式 | 主要适用任务 |
| --- | --- | --- | --- |
| E01 | 边界过短 | 丢掉领域、对象、级别、数量、否定或范围限定 | 实体抽取 |
| E02 | 边界过长/不够简洁 | 带入“负责、要求、优先”等句式壳或整句解释 | 实体抽取 |
| E03 | 合并/拆分错误 | 多个并列项被合并，或一个完整实体被错误拆开 | 实体抽取、子类枚举 |
| E04 | 字段混淆 | location/workPlace/company、职责/要求/优先项等放错字段 | 实体抽取 |
| E05 | 类别混淆 | 选择语义相邻但错误的合法类别 | 6 类分类任务、岗位分类 |
| E06 | 层级/路径不一致 | level1/2/3 不属于同一路径，父类错误，子类漏项/增项 | 岗位分类、2 类 taxonomy 任务、工作时间 |
| E07 | 幻觉/过度推断 | 补充原文未出现实体，或从薪资单位、常识、公司名推导标签 | 全任务 |
| E08 | 遗漏 | 应抽字段为空、数组漏项、children 不完整 | 实体抽取、子类枚举 |
| E09 | “其他”校准错误 | 可明确分类却输出“其他”，或信息不足却强行具体分类 | 闭集分类 |
| E10 | 规则例外错误 | 违反 position[1]、workMode、原文逐字、level2 原实体回退等特例 | 实体抽取、工作场所 |
| E11 | JSON/schema 错误 | 非 JSON、额外解释、错 key、错值类型、额外 level4/level5 | 全任务 |

## 4. 目标规模与任务配额

首轮建议不是 10 万条，而是 10,000 条高置信、可审计的 hard/medium preference pair。当前 SFT 已具备强格式能力，过量低质量 DPO 更可能造成能力回退。后续是否扩容由 Stage 4 的线上真实错误决定。下表的任务比例与四阶段比例按本计划锁定，生成候选和最终验收集都按同一比例执行；某一切片质量不足时先补生成候选，不得擅自挪用其他任务配额。

| 任务 | 总配额 | 占比 | Stage 1 Pilot | Stage 2 核心规则 | Stage 3 困难/长尾 | Stage 4 模型闭环 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `entity_extraction` | 4,000 | 40.0% | 400 | 1,500 | 1,440 | 660 |
| `job_name_classification` | 3,200 | 32.0% | 300 | 1,300 | 1,140 | 460 |
| `work_time_classification` | 700 | 7.0% | 80 | 300 | 240 | 80 |
| `workplace_classification` | 600 | 6.0% | 60 | 250 | 210 | 80 |
| `benefit_classification` | 600 | 6.0% | 60 | 250 | 210 | 80 |
| `work_type_classification` | 250 | 2.5% | 30 | 100 | 80 | 40 |
| `settlement_classification` | 250 | 2.5% | 30 | 100 | 80 | 40 |
| `taxonomy_leaf_to_parent` | 200 | 2.0% | 20 | 100 | 50 | 30 |
| `taxonomy_level2_to_children` | 200 | 2.0% | 20 | 100 | 50 | 30 |
| **合计** | **10,000** | **100%** | **1,000** | **4,000** | **3,500** | **1,500** |

配额是验收后数量，不是生成候选数。建议按 1.5–2.0 倍生成候选，经过规则、模型裁判和人工抽检后再落盘。若某类不能形成明确 hard negative，不为凑数保留弱偏好对。

## 5. 各任务的错误配额和生成重点

### 5.1 `entity_extraction`：4,000 对

| 子目标 | 计划数量 | 生成重点 |
| --- | ---: | --- |
| 边界过短/过长、简洁性 | 1,800 | position 与长数组字段的最短充分表达；过短和过长必须双向覆盖 |
| 字段混淆 | 900 | company/location/workPlace；description/responsibilities/requirements/preferredQualifications/benefits；salary/salaryPayment；employmentType/workMode |
| 幻觉与过度推断 | 600 | 常识补全、由公司/地点/薪资单位推断、改写原文、隐含福利或工作方式 |
| 遗漏与召回保持 | 400 | 多实体、多职责、多要求、否定条件、数值范围、并列技能漏项 |
| JSON/schema | 200 | 只取模型真实出现过的格式错误，不做随机构造 |
| 规则例外 | 100 | `position[1]` 归纳边界、workMode 标准化、空字段类型、position 最多两项 |

“简洁但不缺失重点”采用最短充分短语规则：

- 职责至少保留可识别的动作与对象；涉及业务/工具/技术/指标时保留能区分职责的限定项。
- 要求至少保留能力/资格及其必要程度、年限、学历、证书、语言、工具或行业限定。
- 优先项保留“优先”语义所约束的具体条件，但 chosen 中不重复整句句式壳。
- 任何缩短若丢失否定词、数量、范围、技术对象、行业对象、资历或强弱程度，均归为 rejected。
- 除 `position[1]`、标准化 `workMode` 外，chosen 的每个非空值都必须能在输入中逐字定位。

字段分阶段：

| 阶段 | 字段范围 |
| --- | --- |
| Stage 1 | position、company、location、workPlace、salary、salaryPayment、employmentType、schedule、education、workExperience，并用少量长字段验证“简洁性”裁判规则 |
| Stage 2 | responsibilities、requirements、preferredQualifications、benefits、description 的单字段原子偏好；同步覆盖短字段边界和跨字段混淆 |
| Stage 3 | 多字段同时出现、并列项、长文本、弱标题、搜索短语、否定与条件限定；仍保持每对只有一个主要错误 |
| Stage 4 | SFT/DPO 候选模型在未见业务语料上的真实错例，优先收集边界与字段混淆 |

### 5.2 `job_name_classification`：3,200 对

建议结构：合法相邻类别混淆约 65%，路径一致性 15%，忽略上下文 10%，候选外幻觉 5%，JSON/schema 5%。所有 chosen 必须是 `job_cate.json` 中的合法唯一三级路径；rejected 优先取同一 level2 内的近邻三级类，其次取已观察到的跨 level1/level2 混淆。类别名称、层级和路径不得由生成模型自行改写。

| 阶段 | 类别覆盖 |
| --- | --- |
| Stage 1 | SFT 头部 12 个一级类：生产制造、零售/生活服务、互联网/AI、医疗健康、教育培训、销售、房地产/建筑、电子/电气/通信、客服/运营、直播/影视/传媒、设计、餐饮；优先汽车↔生产制造、电子↔互联网、教育↔零售、直播↔市场等已观察混淆边 |
| Stage 2 | 其余 14 个一级类：市场/公关/广告、金融、人力/行政/法务、物流/仓储/司机、咨询/翻译/法律、财务/审计/税务、产品、采购/贸易、酒店/旅游、能源/环保/农业、汽车、高级管理、项目管理、其他；补齐 155 个二级路径的有效覆盖 |
| Stage 3 | 1,058 个三级标签中的尾部类别、重名/近义职位、同名跨父类职位、弱岗位名与强上下文消歧；不把有歧义的三级名用于 leaf-to-parent 任务 |
| Stage 4 | 由当前 SFT 模型和阶段 DPO 模型真实预测产生的 confusion graph 定向采样 |

类别配额不按 SFT 频次简单等比例：`job_cate.json` 中每个一级类至少有 30 对；每个二级路径至少有 4 对候选覆盖；1,058 条三级路径的长尾采用“有真实语料则至少 1 对、无可靠语料不凭空造标签”的原则。高 PV 搜索词与真实职位详情各占一定比例，避免只会处理完整职位描述。

### 5.3 `taxonomy_leaf_to_parent`：200 对

- 只使用标准分类树中父类唯一的三级名称。
- Stage 1/2 覆盖岗位分类高混淆路径；Stage 3 覆盖低频一级类和相邻父类；Stage 4 收集模型真实路径错误。
- rejected 只能是合理的近邻父路径或模型真实错路，不能把完全无关一级类随机拼接。
- chosen/rejected 都必须使用固定 schema；chosen 的 level1/2/3 必须形成真实路径。

### 5.4 `taxonomy_level2_to_children`：200 对

- Stage 2 前覆盖全部 155 个一级/二级完整路径至少一次；剩余配额投向 children 较多、名称相近或容易漏项的路径。
- 错误结构建议：漏一个困难子类 35%、多一个近邻子类 35%、混入其他二级的同名/近义子类 15%、JSON/数组错误 15%。
- 不用随机乱序作为唯一偏好差异，除非评测和业务明确要求顺序。

### 5.5 `work_type_classification`：250 对

合法类别仅为：短期工、假期工、学生工、兼职工、实习生、大龄工、长期工、周末工、其他。

- Stage 1 即覆盖全部 9 类。
- 重点混淆：短期工/兼职工、假期工/学生工、学生工/兼职工、实习生/学生工、周末工/兼职工、长期工/其他。
- 对现有低频类别周末工、大龄工、学生工、假期工提高采样权重。
- 必须包含 employmentType 与 workMode 的跨任务隔离负例，但不改变任务 schema。

### 5.6 `workplace_classification`：600 对

合法一级类共 22 类；二级优先取提示词候选，只有具体公司、工厂或场所名无法精确匹配时才允许 level2 原实体回退。

| 阶段 | 类别覆盖 |
| --- | --- |
| Stage 1 | 公司、零售店、社区住宅、教育培训机构、工厂、交通站、医院、餐饮店等高频一级类，重点做公司/工厂/园区/仓库/社区住宅混淆 |
| Stage 2 | 补齐其余一级类：酒店、生活服务店、康养中心、美容美发店、旅游景点、休闲娱乐场所、运动健身场所、文化机构、汽车服务点、金融机构、仓库、工地、政府机构、自然景观，并覆盖标准二级路径 |
| Stage 3 | 具体机构名、品牌名、园区名、医院/酒店/学校等带实体名场景，以及 level2 原实体回退边界 |
| Stage 4 | 真实模型产生的 level1 混淆和错误回退 |

rawWorkPlace 必须原样保留。不得把 open-text level2 随机替换成另一个实体名构造 rejected。

### 5.7 `settlement_classification`：250 对

合法类别仅为：日结、计件、半月结、月结、周结、小时结、其他。

- Stage 1 即覆盖全部 7 类。
- 至少 30% 用于“薪资单位不是结算方式”：元/天不等于日结，元/小时不等于小时结。
- 强化低频半月结、小时结、周结，但必须有明确文本证据。
- “多劳多得/按件计酬”“每天下班发”“月底发”等口语表达用于相邻 hard negative。

### 5.8 `work_time_classification`：700 对

合法类别为提示词中的 28 个父子组合加“其他”，且非“其他”时必须满足 `fullCategory = level1 + "-" + level2`。

| 阶段 | 类别覆盖 |
| --- | --- |
| Stage 1 | 其他、白班制-长白班、双休制-双休、任务交付制-时间自由、轮班制-两班倒、单休制-单休、半天班-上午班/下午班、弹性工时制-核心弹性、单休制-月休四天、待命响应制-轮值待命、长短周制-大小周 |
| Stage 2 | 首次补齐其余 17 类：单休制-996、调休累积制-加班调休、项目周期制-忙闲季交替、小时工-上午钟点/下午钟点/晚间钟点/不定时钟点、轮班制-上M休N/三班倒/做一休一/做二休二/做三休三、夜班制-通宵班/大夜班、集中轮休制-做一休二、住家制-住家保姆/月嫂 |
| Stage 3 | SFT 极低频类：轮班制-做三休三、住家制-住家保姆、住家制-月嫂、单休制-996、轮班制-做二休二、集中轮休制-做一休二，以及信息不足应归“其他”的反例 |
| Stage 4 | 模型真实“过度输出其他”和错误 fullCategory 路径 |

### 5.9 `benefit_classification`：600 对

标准候选共 43 个词，分类只能使用提示词原词。当前 SFT 实际分布中“长期照护险”未见训练覆盖，员工援助计划(EAP)、各单项保险等也极低频，必须在可靠语义前提下补齐。

| 阶段 | 类别覆盖 |
| --- | --- |
| Stage 1 | 其他、内部培训、内部晋升通道、绩效奖金、团建旅游、销售提成、节日福利、五险一金、餐补/工作餐、导师制、带薪年假、包住；同时覆盖包吃/包住/包吃包住的语义扩大 |
| Stage 2 | 首次补齐其余 31 类：年终奖、项目奖金、全勤奖、股票期权、养老保险、医疗保险、失业保险、工伤保险、生育保险、住房公积金、补充医疗保险、意外险、重疾险、年度体检、长期照护险、弹性工作制、远程办公、带薪病假、交通补贴/班车、住房补贴/宿舍、包吃包住、包吃、外部培训、技能认证报销、学历教育补助、生日福利、结婚贺礼、生育贺礼、家属关怀、员工援助计划(EAP)、零食下午茶 |
| Stage 3 | 长期照护险、员工援助计划(EAP)、失业/工伤/生育/医疗/养老等尾部标签，以及无法落入标准词时的“其他” |
| Stage 4 | 模型真实“其他”过用和语义扩大错例 |

## 6. 分阶段执行计划

### Stage 0：基线冻结与错误图谱（不生成训练对）

1. 固化 SFT 基线模型、提示词版本、`job_cate.json` 哈希、其余任务候选快照和 9 个任务的 schema。
2. 从 diagnostic 数据而非 frozen test 汇总真实错误，形成 `task × category × error_type × confusion_target` 图谱。
3. 建立 train/dev/test 的 source_id、标准化输入、近重复簇和业务实体名黑名单。
4. 给实体长字段制定双向裁判规则：既惩罚冗长，也惩罚丢失标识信息。
5. 建立 SFT output 屏蔽机制，确认生成模型和 A/B 审核模型均无法读取旧标签。
6. 校验现有 `llm_generated_v1` 的来源、元数据和回归表现；因其生成口径与 v1.1 不同，只能作为风险参考，不能自动计入 Pilot 或正式验收集。

退出条件：基线报告、混淆图、合法类别快照、泄漏黑名单和验收脚本均可复现。

### Stage 1：1,000 对 Pilot

1. 60% 使用 SFT 原始输入重新标注，40% 为基于同类业务形态的 LLM 新写场景；两部分 chosen 均由大模型独立生成，均不读取 SFT 旧 output。
2. 难度比例建议 easy 10%、medium 60%、hard 30%；easy 只用于校准 schema 和明确规则，不大量扩充。
3. 实体长字段先小规模验证裁判一致性，不在规则未稳定时一次生成上千条。
4. 单独训练 Pilot adapter，和 SFT 基线做逐任务回归。

退出条件：所有质量门通过，目标切片提升，JSON/岗位分类无明显回退；否则修改生成规则，不进入 Stage 2。

### Stage 2：4,000 对核心规则覆盖

1. 覆盖所有小闭集类别、22 个 workplace 一级类、29 个 work-time 类、43 个 benefit 类和全部 155 个 taxonomy level2 路径。
2. 扩充实体抽取的单字段边界与跨字段混淆；长字段使用“最短充分短语”双裁判。
3. 岗位分类以 26 个一级类和 155 个二级路径为配额骨架，不按头部频次淹没尾部。
4. 每 1,000 条形成一个可独立回滚的数据 shard，逐 shard 验证。

退出条件：类别覆盖达标；规则校验 100%；累计模型在目标任务上提升且全局指标不越过回归红线。

### Stage 3：3,500 对困难与长尾

1. 只生成相邻类别、同名跨父类、弱标题强上下文、长文本多实体、否定/数量/范围等 hard negative。
2. 提升岗位三级长尾、work-time/benefit 极低频类和具体场所回退边界。
3. hard pair 必须能写出明确、短的偏好理由，并通过独立裁判；无法稳定判断的 pair 进入人工队列，不进训练集。
4. 控制同一 confusion edge 的模板重复，单一错误边不超过对应任务的 8%。

退出条件：hard slice 有提升；head 类不回退；近重复和固定模板率在阈值内。

### Stage 4：1,500 对模型闭环

1. 用通过 Stage 3 的模型在全新、非评测业务语料上采样多个候选。
2. 只保留模型真实犯错且 chosen 可高置信确定的样本；模型已经稳定答对的场景不硬造 rejected。
3. 任务数量仍严格遵守总配额表中 Stage 4 的比例；只允许在每个任务内部按最新错误分布调整错误类型和类别优先级。
4. 形成最终 v1.1 数据集；后续版本以相同流程小步迭代。

退出条件：最终冻结评测通过，且没有任务级能力倒退。

## 7. LLM 生成与筛选流水线

1. **锁定候选**：解析 `job_cate.json` 生成职位三级路径快照；解析 `label_prompts_v2.md` 各任务候选生成其余闭集快照。保存文件哈希和候选数量，生成期间禁止动态改类。
2. **选种子**：按已锁定的任务、类别、错误类型、来源类型和难度配额，从 SFT 原始 input 中选取未泄漏种子；程序层面移除/屏蔽旧 output。
3. **大模型生成 chosen**：生成模型依据 system prompt、原始 input 和权威候选独立标注。SFT 旧 output、历史 DPO chosen 和 frozen-test 答案均不进入上下文。
4. **大模型生成 rejected**：按本计划任务内错误比例生成 1～3 个候选 rejected，再选取最贴近真实模型错误且与 chosen 偏好明确的一项；可利用 confusion graph 指定错误方向，但不得复制既有答案。
5. **生成新场景**：仅在类别覆盖不足时由大模型按招聘语料风格新写输入；新场景不得照搬 frozen test、公司名、完整句子或答案。
6. **原子化**：chosen/rejected 保持相同 schema，原则上只改变一个主要业务错误；其他字段保持一致。
7. **规则校验**：JSON、schema、类型、候选集合、taxonomy 路径、原文 span、数组基数、空值类型全部自动校验。
8. **独立裁判**：生成与裁判分离；裁判按项目提示词和权威候选判断匿名 A/B 中哪项更优，并输出不进入训练文件的审核理由和置信度；不允许拿 SFT 旧 output 当裁判答案。
9. **人工抽检**：Pilot 100% 审核；Stage 2 每类至少 20% 且长字段 50%；Stage 3 hard pair 至少 30%；Stage 4 真实错例至少 20%。
10. **去重与防泄漏**：按 exact、normalized、source_id、近重复簇、公司/职位组合和模板指纹检查。
11. **物化训练格式**：审核主表保留完整 metadata；最终再转换为 LLaMAFactory ShareGPT ranking，不能只保留三段文本后丢失审计信息。

## 8. 审核主表必须保留的元数据

最终训练 JSONL 可以只含训练所需字段，但源数据主表/sidecar 至少保留：

- `pair_id`、`dataset_version`、`prompt_version`、`job_cate_hash`、`candidate_snapshot_hash`
- `task`、`source_type`、`source_id`、`source_split`、`scenario_group_id`
- `primary_error_type`、`secondary_error_types`、`target_field`
- `chosen_category`、`rejected_category`、`confusion_edge`
- `difficulty`、`generation_method`、`generator_version`
- `chosen_provenance`、`rejected_provenance`；正式数据中 chosen provenance 必须标明为大模型独立生成，而非 SFT 标签复制
- `judge_decision`、`judge_confidence`、`review_reason`
- `human_review_status`、`validator_results`
- `exact_hash`、`normalized_hash`、`near_duplicate_cluster`

没有任务、错误类型、类别和来源元数据的 pair 不进入正式版本，否则无法按阶段回归和定位负迁移。

## 9. 质量门禁

### 9.1 单条硬门禁

- chosen/rejected 均可解析为一个 JSON 对象，schema 和字段类型 100% 正确。
- chosen 不等于 rejected，且有明确业务偏好，不是纯空格、顺序或无关改写差异。
- 职位及 taxonomy chosen 100% 属于 `job_cate.json`；其余分类 chosen 100% 属于当前任务提示词候选；候选外类别一律为 0。
- 实体 chosen 除允许例外外 100% 原文可定位；不得出现输入外实体。
- rejected 是合理模型错误，且至少通过一个来源证明：真实模型输出、已观察 confusion edge 或严格业务扰动。
- 同一 pair 尽量只有一个 primary error；若错误耦合无法拆开，必须标记并进入 hard 审核。
- 与所有冻结评测集 exact/normalized/source/near-duplicate overlap 均为 0。

### 9.2 数据集级门禁

- 重复 pair 为 0；重复 prompt 原则上为 0，必要的一对多候选必须显式分组。
- hard 占 25%–40%，medium 占 50%–65%，easy 不超过 15%。
- 单一模板不超过总集 1%，单一 confusion edge 不超过对应任务 8%。
- `job_cate.json` 的 26 个 level1、155 个 level2 和 1,058 条 level3 路径按计划覆盖；workplace 22 个 level1、work-time 29 类、work-type 9 类、settlement 7 类、benefit 43 类全部有审核覆盖。
- 所有 Stage 都单独有 manifest、配额报告、验证报告、人工抽检记录和模型回归报告。

## 10. 评估指标与阶段放行阈值

### 10.1 全局回归红线

以当前 SFT quick 30% 为基线，每个阶段训练后至少满足：

- JSON Parse 不低于 99.8%，且相对基线下降不超过 0.1 个百分点。
- Schema Exact 不低于 99.8%，且不得新增稳定的错 key、额外 level4/level5。
- Micro Field Exact 不得下降超过 0.3 个百分点。
- 任一任务 Object Exact 不得下降超过 1 个百分点；低样本任务同时看完整人工集，避免小样本误判。

### 10.2 目标提升指标

| 目标 | 指标 | 首轮期望 |
| --- | --- | --- |
| 实体边界 | position Set F1、各字段 span F1 | +1.5～3.0 pp |
| 简洁且完整 | 关键槽位保留率、冗余率、人工 preference win rate | 保留率不降，冗余率下降 20% 以上 |
| 长字段 | responsibilities/requirements Set F1 | 各 +3 pp 以上 |
| 岗位分类 | level3 accuracy、Object Exact、confusion-edge accuracy | +3 pp 以上 |
| 工作时间 | fullCategory/Object Exact | +3 pp 以上 |
| 工作场所 | level1/level2/Object Exact | +2 pp 以上 |
| 幻觉 | 输入外实体率、候选外标签率 | 相对下降 30% 以上，候选外标签为 0 |
| JSON | Parse/Schema Exact | 保持基线，不以牺牲格式换业务提升 |

“简洁性”不能只用平均长度衡量。必须同时统计：原文可定位率、动作/对象/技术/行业/数量/否定/资历等关键槽位保留率、重复词和句式壳比例、人工双盲偏好胜率。

## 11. 交付物规划

每一阶段应产出以下文件，但本计划阶段暂不生成：

1. 审核主表 JSONL：含 prompt、chosen、rejected 和完整 metadata。
2. LLaMAFactory ShareGPT ranking 训练文件。
3. 独立 dev 文件；按 scenario/source group 隔离，不从同模板随机切行。
4. `manifest.json`：版本、来源、配额、提示词哈希、`job_cate.json` 哈希和各任务候选快照哈希。
5. `validation_report.json`：规则、类别、路径、重复和泄漏报告。
6. `distribution_report.md`：任务 × 错误类型 × 类别 × 难度分布。
7. `human_review_report.md`：抽检规模、争议率、修改率和主要问题。
8. `stage_evaluation_report.md`：相对 SFT 及上一阶段的业务指标变化。

## 12. 推荐实施顺序

1. 先完成 Stage 0，锁定 `job_cate.json` 与其余任务候选快照；现有 1,000 条 `llm_generated_v1` 不直接沿用，按 v1.1 口径重新生成 Pilot。
2. 以实体短字段、岗位真实混淆、工作时间“其他”校准组成 Stage 1 Pilot。
3. Pilot 通过后再扩展实体长字段的“简洁但完整”数据；若裁判一致率不足，暂停该切片而不是降低审核标准。
4. Stage 2 完成合法类别广覆盖，Stage 3 才做长尾和复杂 hard negative。
5. 只有通过 Stage 3 的模型才能用于 Stage 4 真实错误采样。
6. 每阶段只合并带来净收益的 shard；任何造成 JSON、岗位分类或头部类别回退的 shard 均隔离复查。

该顺序的核心是：先证明偏好定义正确，再扩大数量；先修正模型真实错误，再补足长尾覆盖；任何局部提升都不能以全局 schema 和岗位分类能力回退为代价。

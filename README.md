# 加个鸡腿 🍗

让闲钱的差别看得见。中文货币基金公开资料观察、条件筛选、假设收益差试算与完整逐日历史回放。独立静态 H5，无 GPT 域名、账户登录或第三方前端依赖。

线上：https://cuilei0705-rgb.github.io/fund-observer-h5/

## 本地运行

Python 3.12+、Node 24、系统 curl；不需要 npm 包。

```sh
python3 scripts/refresh.py
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/core.test.cjs
python3 scripts/build.py
python3 -m http.server 8765 --directory dist
```

`src/` 是维护源；`data/` 保存带日期及来源哈希的真实快照；`scripts/refresh.py` 执行发现、去重、渠道及历史更新；`scripts/build.py` 生成根 `index.html` 和 `dist/`。GitHub Actions 每日北京时间08:23尝试刷新、测试、保留数据与状态并部署。任务可能延迟；公共仓库长期不活跃可能被 GitHub 停止计划任务，需检查 Actions。配置存在不代表已经成功运行。

## 正确理解结果

- 不宣称全市场、全渠道、全部存续或可购买；A/B/C份额独立识别，基金管理人归属未系统核验。
- 同一披露日普通货币基金才入两个收益榜；浮动净值类别不混排。缺失不是0，新快照不以旧值补齐。
- 收益超过3个自然日暂停条件匹配，渠道超过7天排除候选。候选仅表示公开门槛相符，不证明取用能力。
- 卡快赎额度、到账时效、服务时间、消费支付未知时不给出确定推荐；极速回活期宝不等于到银行卡。
- 余额宝20只样本来自2019-04-22历史报道，不是当前接入名单或账户可选清单。
- 未来情景：本金×假设年收益率×计息天数÷365，候选扣除等待与费用；基准全程计息。不是复利预测或收益承诺。
- 历史回放：双方每个自然日都须有普通货币口径万份收益；固定份额、不复投、不计交易费用与等待；不冒充个人到账。

详见 `docs/OPERATIONS.md`。原发布版本保存在 Git 历史 `c1339d1`，原工程未删除。

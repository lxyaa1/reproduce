# 作者数据确认邮件草稿

状态：仅起草，尚未发送。收件地址来自作者公开代码仓库 README 的 Contact 部分。发送前替换姓名与单位占位符。

To: hcwang@ir.hit.edu.cn

Subject: Question about the AMBIFC evaluation data in “Beyond Frameworks” (ACL 2025)

Dear Haochun Wang and co-authors,

I am a graduate student reproducing the SES/EBFC experiments in your paper, “Beyond Frameworks: Unpacking Collaboration Strategies in Multi-Agent Systems,” using MASFactory. Thank you for sharing the code.

I would appreciate some clarification about the exact AMBIFC evaluation data. The preprocessing example in `fact_code/filter_claim_data.py` refers to `test.certain.jsonl`, while the experiment scripts load `filtered_test_certain_processed.json`.

Running the two published preprocessing functions on my copy of `test.certain.jsonl` produces 501 samples: 409 supporting and 92 refuting. All 10 examples in your `data_example.json` match our processed samples exactly, including evidence order.

Could you please clarify:

1. Did the reported SES/EBFC experiments use only `test.certain.jsonl`, or also other files such as `test.uncertain.jsonl` or the train/dev splits? Which AMBIFC release did you use?
2. Was the final evaluation set these 501 samples, or was any additional filtering or sampling performed after the published preprocessing? Were the same samples used for all single-agent baselines and multi-agent configurations?
3. If possible, could you share the final processed evaluation file, or alternatively the evaluated claim IDs and any additional preprocessing steps? This would help us ensure that our evaluation uses the same data as the paper.

Any clarification would be very helpful. Thank you for your time.

Best regards,
[Your name]
[University / Department]

## 中文说明

邮件只聚焦目前开展的 AMBIFC 实验，给出已经完成的核对结果，便于作者直接确认。主要询问原始文件/发布版本、501 条是否为完整评测集，以及能否提供最终文件或样本 ID；不把尚未验证的 501 条称为论文确定使用的数据。

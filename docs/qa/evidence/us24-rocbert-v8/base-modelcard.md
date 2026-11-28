---
language:
- zh

pipeline_tag: "fill-mask"

widget:
- text: "ba黎系[MASK]国的首都"
  example_title: "Adversarial Attack Test"
---

# RoCBert

## Introduction

RoCBert is a pretrained Chinese language model that is robust under various forms of adversarial attacks proposed by WeChatAI in 2022,

More detail: https://aclanthology.org/2022.acl-long.65.pdf

Pretrained code: https://github.com/sww9370/RoCBert

## How to use
```Python
# pip install transformers>=4.25.1

from transformers import AutoTokenizer, AutoModel
tokenizer = AutoTokenizer.from_pretrained("weiweishi/roc-bert-base-zh")
model = AutoModel.from_pretrained("weiweishi/roc-bert-base-zh")
```

## Citation

```bibtex
@inproceedings{su2022rocbert,
  title={RoCBert: Robust Chinese Bert with Multimodal Contrastive Pretraining},
  author={Su, Hui and Shi, Weiwei and Shen, Xiaoyu and Xiao, Zhou and Ji, Tuo and Fang, Jiarui and Zhou, Jie},
  booktitle={Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages={921--931},
  year={2022}
}
```
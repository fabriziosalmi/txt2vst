---
dataset_info:
  features:
    - name: prompt
      dtype: string
    - name: completion
      dtype: string
  splits:
    - name: train
      num_examples: 10000
license: mit
task_categories:
  - text-generation
tags:
  - audio
  - vst
  - music
  - code-generation
  - structured-output
language:
  - en
size_categories:
  - 10K<n<100K
---

# txt2vst Dataset

**10,000 natural-language-to-VST-spec pairs for music plugin generation.**

## Dataset Description

Each sample maps a natural language description of a VST instrument to a structured `spec.json` that defines the complete plugin architecture.

### Fields
- `prompt`: Natural language description (e.g., "drum machine with kick snare and acid bass, punchy mastering")
- `completion`: Compact JSON spec defining the plugin (voices, FX, theme, mastering chain)

### Coverage
| Component | Options |
|---|---|
| Drum voices | kick, snare, hats, tom, perc, clap |
| Pitched voices | bass_acid, lead, pad, pluck, organ, fm_synth, noise, string, brass, sub_bass |
| FX | delay, reverb, chorus, compressor, distortion, phaser, eq, gate |
| Themes | 24 (midnight, void, obsidian, acid, neon, glow, strobe, matrix, ember, solar, copper, candy, frost, chrome, arctic, vapor, industrial, terminal, hologram, white, cream, blood, lavender) |
| Mastering | bypass, transparent, punch, wet, radio, distorted, wide |

### Combinatorial Space
- **10M+** sonically unique combinations
- **2.7B+** visually distinct configurations
- **16** prompt templates with natural variation

## Usage

```python
from datasets import load_dataset
ds = load_dataset("fabriziosalmi/txt2vst", split="train")
print(ds[0])
```

## Generation

```bash
python3 dataset/generate_dataset.py --count 10000 --output dataset/train.jsonl
```

## License
MIT — same as the [txt2vst](https://github.com/fabriziosalmi/txt2vst) engine.

## Links
- [txt2vst GitHub](https://github.com/fabriziosalmi/txt2vst)
- [txt2vst.com](https://txt2vst.com)
- [HF Space](https://huggingface.co/spaces/fabriziosalmi/txt2vst)

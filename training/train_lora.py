"""
LoRA fine-tuning of Gemma 4 31B on training/train.jsonl, on one GPU (e.g. a Verda instance).
Steps and GPU choice: FINE_TUNING.md, step 11.

    pip install unsloth                                   # pulls torch, transformers, peft, trl
    export HF_TOKEN=...                                   # read access to google/gemma-4-31B-it

    python train_lora.py --check                          # no GPU needed: lengths + what is trained on
    python train_lora.py --max-steps 5                    # smoke test
    python train_lora.py                                  # full run (2 epochs), adapter in out/adapter
    python train_lora.py --merge-to out/merged            # same, then write merged 16-bit weights
    add --qlora on an 80 GB GPU (4-bit base, ~22 GB); without it the base is bf16 (~62 GB + training)

Each example is rendered with the base model's own chat template and the same tool
definitions the app sends, so the trained format matches what vLLM's gemma4 parser
reads on Verda. Each assistant turn is its own example: the prompt exactly as vLLM builds
it (not trained on), then the tool call or answer (trained on). Never trained on: the
system prompt, questions or tool results.

Written without a GPU to test on: run --check and a --max-steps 5 run before the full run.
"""

import argparse
import json
from pathlib import Path

BASE = "google/gemma-4-31B-it"  # what the Verda deployment serves
HERE = Path(__file__).parent


def load(name):
    return [json.loads(line) for line in (HERE / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def as_template_messages(messages):
    """vLLM parses tool-call arguments into dicts before applying the chat template; do the same."""
    out = []
    for m in messages:
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [
                {**c, "function": {**c["function"], "arguments": json.loads(c["function"]["arguments"] or "{}")}}
                for c in m["tool_calls"]
            ]
        out.append(m)
    return out


def render(tokenizer, messages, tools, generation_prompt=False):
    return tokenizer.apply_chat_template(messages, tools=tools, tokenize=False,
                                         add_generation_prompt=generation_prompt)


# What Gemma 4's template adds to a generation prompt but leaves out of the same turn in
# the history: an empty thinking block. vLLM sends it, so the training prompt must too.
EMPTY_THOUGHT = "<|channel>thought\n<channel|>"


def encode(tokenizer, record):
    """One example per assistant turn: the prompt exactly as vLLM builds it (not trained on)
    and what the model wrote, a tool call or the answer (trained on).

    Gemma 4 renders a turn differently in the history than as a generation prompt (see
    EMPTY_THOUGHT), so one long sequence per conversation would not match the app.
    """
    messages, tools = as_template_messages(record["messages"]), record["tools"]
    examples = []
    for i, m in enumerate(messages):
        if m["role"] != "assistant":
            continue
        prompt = render(tokenizer, messages[:i], tools, generation_prompt=True)
        upto = render(tokenizer, messages[: i + 1], tools)
        shared = prompt[: -len(EMPTY_THOUGHT)] if prompt.endswith(EMPTY_THOUGHT) else prompt
        if not upto.startswith(shared):
            raise ValueError(f"{record['id']} turn {i}: the prompt is not the start of the conversation")
        completion = upto[len(shared):]
        p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        c_ids = tokenizer(completion, add_special_tokens=False)["input_ids"]
        examples.append({"input_ids": p_ids + c_ids, "attention_mask": [1] * (len(p_ids) + len(c_ids)),
                         "labels": [-100] * len(p_ids) + c_ids, "id": f"{record['id']}#{i}"})
    return examples


def check(tokenizer, train, val, max_len):
    examples = [e for r in train + val for e in encode(tokenizer, r)]
    lengths = sorted(len(e["input_ids"]) for e in examples)
    print(f"{len(examples)} training examples (one per assistant turn) from {len(train) + len(val)} "
          f"conversations; tokens: median {lengths[len(lengths) // 2]}, max {lengths[-1]} (limit {max_len})")
    record = next(r for r in train if any(m.get("tool_calls") for m in r["messages"]))
    for e in encode(tokenizer, record):
        n = sum(1 for lab in e["labels"] if lab == -100)
        print(f"\n=== {e['id']}: prompt ends with ===\n{tokenizer.decode(e['input_ids'][max(0, n - 25):n])!r}")
        print(f"--- trained on ---\n{tokenizer.decode(e['input_ids'][n:])}")
    print("\nThe trained parts should be only tool calls and the final answer; each prompt should end "
          "where the model starts writing.")
    return lengths[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="show lengths and trained parts, then stop")
    p.add_argument("--qlora", action="store_true", help="4-bit base (fits an 80 GB GPU)")
    p.add_argument("--max-len", type=int, default=12288)
    p.add_argument("--epochs", type=float, default=2)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--max-steps", type=int, default=-1, help="stop early (smoke test)")
    p.add_argument("--out", type=Path, default=Path("out"))
    p.add_argument("--merge-to", type=Path, help="also write merged 16-bit weights here")
    args = p.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(BASE)
    train, val = load("train.jsonl"), load("val.jsonl")
    longest = check(tokenizer, train, val, args.max_len)
    if longest > args.max_len:
        raise SystemExit(f"a conversation has {longest} tokens; raise --max-len (never truncate: "
                         "the answer is at the end)")
    if args.check:
        return

    from unsloth import FastModel  # import before transformers' trainer so Unsloth can patch it
    from datasets import Dataset
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

    model, _ = FastModel.from_pretrained(
        model_name=BASE, max_seq_length=args.max_len, dtype=None,
        load_in_4bit=args.qlora, load_in_16bit=not args.qlora, full_finetuning=False,
    )
    model = FastModel.get_peft_model(
        model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none",
        use_gradient_checkpointing="unsloth", random_state=3407,
    )

    def dataset(records):
        rows = [e for r in records for e in encode(tokenizer, r)]
        return Dataset.from_list([{k: e[k] for k in ("input_ids", "attention_mask", "labels")} for e in rows])

    train_ds, val_ds = dataset(train), dataset(val)
    trainer = Trainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
        args=TrainingArguments(
            output_dir=str(args.out / "checkpoints"),
            per_device_train_batch_size=1, gradient_accumulation_steps=4,
            num_train_epochs=args.epochs, max_steps=args.max_steps,
            learning_rate=args.lr, warmup_steps=5, lr_scheduler_type="linear", weight_decay=0.001,
            optim="adamw_8bit", bf16=True, logging_steps=1,
            eval_strategy="steps", eval_steps=50, save_strategy="epoch",
            report_to="none", seed=3407, remove_unused_columns=False,
        ),
    )
    trainer.train()
    print("validation:", trainer.evaluate())

    model.save_pretrained(str(args.out / "adapter"))
    tokenizer.save_pretrained(str(args.out / "adapter"))
    print(f"adapter -> {args.out / 'adapter'}")
    if args.merge_to:
        # Unsloth's merge into full 16-bit weights, servable by vLLM like the base model.
        model.save_pretrained_merged(str(args.merge_to), tokenizer, save_method="merged_16bit")
        print(f"merged 16-bit model -> {args.merge_to}")


if __name__ == "__main__":
    main()

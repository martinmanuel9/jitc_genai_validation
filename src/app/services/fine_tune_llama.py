# /app/src/app/services/fine_tune_llama.py

from transformers import Trainer, TrainingArguments, LlamaForCausalLM, LlamaTokenizer
import datasets

def fine_tune_llama():
    model = LlamaForCausalLM.from_pretrained("path/to/llama/model")
    tokenizer = LlamaTokenizer.from_pretrained("path/to/llama/tokenizer")

    data_files = {
        "train": "../../data/models/train.txt",
        "validation": "../../data/models/valid.txt"
    }
    raw_datasets = datasets.load_dataset('text', data_files=data_files)
    
    # Tokenize data
    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, padding="max_length")
    tokenized_datasets = raw_datasets.map(tokenize_function, batched=True)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir="../../data/models/llama-finetuned",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        save_steps=1000,
        save_total_limit=2,
        logging_dir='../../logs',
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets['train'],
        eval_dataset=tokenized_datasets['validation'],
    )

    trainer.train()
    model.save_pretrained("../../data/models/llama-finetuned")

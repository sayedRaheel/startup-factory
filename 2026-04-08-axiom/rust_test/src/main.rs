use candle_core::{Device, Tensor};
use candle_nn::VarBuilder;
use candle_transformers::models::bert::{BertModel, Config, DTYPE};
use tokenizers::Tokenizer;

fn main() {
    println!("Loading on-device embedding model...");
    let device = Device::Cpu;
    let api = hf_hub::api::sync::Api::new().unwrap();
    let repo = api.repo(hf_hub::Repo::new("sentence-transformers/all-MiniLM-L6-v2".to_string(), hf_hub::RepoType::Model));
    
    let config_filename = repo.get("config.json").unwrap();
    let tokenizer_filename = repo.get("tokenizer.json").unwrap();
    let weights_filename = repo.get("model.safetensors").unwrap();

    let config = std::fs::read_to_string(config_filename).unwrap();
    let config: Config = serde_json::from_str(&config).unwrap();
    let tokenizer = Tokenizer::from_file(tokenizer_filename).unwrap();

    let vb = unsafe { VarBuilder::from_mmaped_safetensors(&[weights_filename], DTYPE, &device).unwrap() };
    let model = BertModel::load(vb, &config).unwrap();
    println!("Model loaded successfully");
}

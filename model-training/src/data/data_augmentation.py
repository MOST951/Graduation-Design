import random
from typing import List

class DataAugmentation:
    """Perform data augmentation techniques on text."""

    def __init__(self, synonym_dict: dict = None):
        self.synonym_dict = synonym_dict if synonym_dict else {}

    def synonym_replacement(self, tokens: List[str], n: int = 1) -> List[str]:
        """Replace n words in the sentence with their synonyms."""
        augmented_tokens = tokens[:]
        replaceable_indices = [i for i, token in enumerate(tokens) if token in self.synonym_dict]
        n = min(n, len(replaceable_indices))
        
        for _ in range(n):
            idx_to_replace = random.choice(replaceable_indices)
            synonym = random.choice(self.synonym_dict[augmented_tokens[idx_to_replace]])
            augmented_tokens[idx_to_replace] = synonym
            replaceable_indices.remove(idx_to_replace)
            
        return augmented_tokens

    def random_insertion(self, tokens: List[str], n: int = 1) -> List[str]:
        """Insert n random synonyms into the sentence."""
        augmented_tokens = tokens[:]
        for _ in range(n):
            synonym_to_add = random.choice(list(self.synonym_dict.keys()))
            insert_pos = random.randint(0, len(augmented_tokens))
            augmented_tokens.insert(insert_pos, synonym_to_add)
            
        return augmented_tokens

    def random_deletion(self, tokens: List[str], p: float = 0.1) -> List[str]:
        """Randomly delete words from the sentence with probability p."""
        if len(tokens) == 1:
            return tokens
        
        remaining = [token for token in tokens if random.uniform(0, 1) > p]
        
        if len(remaining) == 0:
            return [random.choice(tokens)] # Return a random token if all are deleted
            
        return remaining

    def back_translation(self, text: str, model_fr, tokenizer_fr, model_en, tokenizer_en) -> str:
        """Back-translation augmentation (requires translation models)."""
        # Translate to French
        inputs = tokenizer_en(text, return_tensors="pt", padding=True, truncation=True)
        translated_ids = model_en.generate(**inputs)
        french_text = tokenizer_en.batch_decode(translated_ids, skip_special_tokens=True)[0]

        # Translate back to English
        inputs_fr = tokenizer_fr(french_text, return_tensors="pt", padding=True, truncation=True)
        translated_ids_fr = model_fr.generate(**inputs_fr)
        back_translated_text = tokenizer_fr.batch_decode(translated_ids_fr, skip_special_tokens=True)[0]

        return back_translated_text

from janome.tokenizer import Tokenizer, Token

t = Tokenizer()
tokens = t.tokenize("Pythonでおしゃべりボットを作る, ")

for token in tokens:
    print(f"単語: {token.surface}, 品詞: {token.part_of_speech}")
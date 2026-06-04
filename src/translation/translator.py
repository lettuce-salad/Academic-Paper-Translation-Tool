"""
Translation Engine
DeepL / Google / Local LLM のフォールバック翻訳
"""
import os
import re
import time
from typing import Optional, Dict, List
from pathlib import Path
import json

# 翻訳API
try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

try:
    from google.cloud import translate_v3 as translate
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from ..protection.protector import ContentProtector


class TranslationEngine:
    """
    翻訳エンジン
    
    フォールバック順序:
    1. DeepL API
    2. Google Translate API
    3. Local LLM (Ollama)
    """

    # Ollama関連の定数
    OLLAMA_TEMPERATURE = 0.1        # 生成温度
    OLLAMA_NUM_CTX = 8192           # コンテキスト長
    OLLAMA_NUM_PREDICT = 6000       # 最大生成トークン
    OLLAMA_MAX_INPUT_CHARS = 6000   # これを超える入力は分割翻訳
    OLLAMA_BATCH_CHARS = 5000       # 分割時の1バッチの最大文字数

    def __init__(self, 
                 deepl_api_key: Optional[str] = None,
                 google_project_id: Optional[str] = None,
                 ollama_model: str = "qwen2.5:7b-instruct-q5_K_M",
                 glossary: Optional[Dict[str, str]] = None,
                 ollama_temperature: Optional[float] = None):
        """
        Args:
            deepl_api_key: DeepL APIキー
            google_project_id: Google Cloud プロジェクトID
            ollama_model: Ollamaモデル名
            glossary: 専門用語辞書 {英語: 日本語}
            ollama_temperature: Ollama生成温度（省略時はクラス定数）
        """
        # 環境変数から取得
        self.deepl_api_key = deepl_api_key or os.getenv("DEEPL_API_KEY")
        self.google_project_id = google_project_id or os.getenv("GOOGLE_PROJECT_ID")
        self.ollama_model = ollama_model
        self.ollama_temperature = (
            ollama_temperature if ollama_temperature is not None
            else self.OLLAMA_TEMPERATURE
        )
        
        # 専門用語辞書
        self.glossary = glossary or {}
        
        # 保護システム
        self.protector = ContentProtector(self.glossary)
        
        # クライアント初期化
        self.deepl_client = None
        self.google_client = None
        
        if DEEPL_AVAILABLE and self.deepl_api_key:
            try:
                self.deepl_client = deepl.Translator(self.deepl_api_key)
            except Exception as e:
                print(f"⚠️  DeepL初期化失敗: {e}")
        
        if GOOGLE_AVAILABLE and self.google_project_id:
            try:
                self.google_client = translate.TranslationServiceClient()
            except Exception as e:
                print(f"⚠️  Google Translate初期化失敗: {e}")
        
        # 使用量カウンター
        self.usage = {
            "deepl": 0,
            "google": 0,
            "ollama": 0
        }
    
    @property
    def uses_api_engine(self) -> bool:
        """API系エンジン（DeepL/Google）が有効か。OllamaのみならFalse。"""
        return bool(self.deepl_client or self.google_client)

    def translate_block(self, content: str, ctx_before=None, ctx_after=None,
                        show_stats: bool = False):
        """
        1ブロックを翻訳する共通ヘルパー（pipeline / resume / page_mode 共用）。

        - DeepL/Google: 指示プロンプトを解釈できないため、翻訳対象テキストのみを送る
        - Ollama: 前後コンテキスト付きプロンプトで文脈を考慮させる

        Returns:
            (訳文, 使用エンジン名)
        """
        ctx_before = ctx_before or []
        ctx_after = ctx_after or []

        if self.uses_api_engine:
            # API系: 生テキストのみ翻訳（プロンプトを送ると指示文まで翻訳されてしまう）
            return self.translate(content, show_stats=show_stats, return_engine=True)
        else:
            # Ollama系: コンテキスト付きプロンプト
            prompt = self._build_context_prompt(content, ctx_before, ctx_after)
            return self.translate(prompt, show_stats=show_stats, return_engine=True)

    def _build_context_prompt(self, content: str, ctx_before: list, ctx_after: list) -> str:
        """Ollama用のコンテキスト付きプロンプトを構築"""
        lines = [
            "以下の学術論文テキストを日本語に翻訳してください。",
            "・である調で統一する",
            "・⟦記号⟧はそのまま保持する",
            "・翻訳文のみを出力し、説明・前置き・後置きは一切不要",
            "",
        ]
        if ctx_before:
            lines.append("【前の文脈（参考・出力不要）】")
            lines.extend(ctx_before)
            lines.append("")
        lines.append("【翻訳対象（この部分のみ日本語訳を出力）】")
        lines.append(content)
        if ctx_after:
            lines.append("")
            lines.append("【後の文脈（参考・出力不要）】")
            lines.extend(ctx_after)
        return "\n".join(lines)

    def translate(self, text: str, show_stats: bool = False,
                  return_engine: bool = False):
        """
        テキストを翻訳。保護→翻訳→復元の順で実行し、
        例外が発生しても必ず protector.clear() を呼ぶ。

        Args:
            text: 翻訳対象テキスト
            show_stats: 統計を表示するか
            return_engine: Trueなら (訳文, エンジン名) のタプルを返す

        Returns:
            str または (str, str)
        """
        if not text.strip():
            return (text, None) if return_engine else text

        try:
            # 保護
            protected_text = self.protector.protect(text)

            if show_stats:
                stats = self.protector.get_stats()
                if stats:
                    print(f"   🔒 保護: {sum(stats.values())}個 ({', '.join(f'{k}:{v}' for k, v in stats.items())})")

            # 翻訳（フォールバック）
            translated_text = None
            engine_used = None

            # 第1層: DeepL
            if self.deepl_client:
                try:
                    translated_text = self._translate_deepl(protected_text)
                    self.usage["deepl"] += len(text)
                    engine_used = "DeepL"
                    if show_stats:
                        print(f"   ✅ DeepL使用")
                except Exception as e:
                    if show_stats:
                        print(f"   ⚠️  DeepL失敗: {e}")
            else:
                if show_stats and self.deepl_api_key:
                    print(f"   ⏭️  DeepL: 初期化失敗")
                elif show_stats:
                    print(f"   ⏭️  DeepL: APIキー未設定")

            # 第2層: Google
            if translated_text is None and self.google_client:
                try:
                    translated_text = self._translate_google(protected_text)
                    self.usage["google"] += len(text)
                    engine_used = "Google"
                    if show_stats:
                        print(f"   ✅ Google使用")
                except Exception as e:
                    if show_stats:
                        print(f"   ⚠️  Google失敗: {e}")
            elif translated_text is None and show_stats:
                if self.google_project_id:
                    print(f"   ⏭️  Google: 初期化失敗")
                else:
                    print(f"   ⏭️  Google: プロジェクトID未設定")

            # 第3層: Ollama
            if translated_text is None:
                if OLLAMA_AVAILABLE:
                    try:
                        translated_text = self._translate_ollama(protected_text)
                        self.usage["ollama"] += len(text)
                        engine_used = "Ollama"
                        if show_stats:
                            print(f"   ✅ Ollama使用")
                    except Exception as e:
                        if show_stats:
                            print(f"   ⚠️  Ollama失敗: {e}")
                else:
                    if show_stats:
                        print(f"   ⚠️  Ollama: パッケージ未インストール")

            # 全エンジン失敗
            if translated_text is None:
                raise RuntimeError(
                    "利用可能な翻訳エンジンがありません。"
                    "DEEPL_API_KEY を設定するか、ollama serve を起動してください。"
                )

            # 復元
            restored_text = self.protector.restore(translated_text)

            if show_stats:
                print(f"   🔓 復元完了 (使用エンジン: {engine_used})")

            return (restored_text, engine_used) if return_engine else restored_text

        finally:
            # 例外が起きても必ずクリア
            self.protector.clear()
    
    def _translate_deepl(self, text: str) -> str:
        """DeepLで翻訳"""
        result = self.deepl_client.translate_text(
            text,
            source_lang="EN",
            target_lang="JA",
            preserve_formatting=True,
        )
        return result.text
    
    def _translate_google(self, text: str) -> str:
        """Google Translateで翻訳"""
        parent = f"projects/{self.google_project_id}/locations/global"
        
        response = self.google_client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": "en",
                "target_language_code": "ja",
            }
        )
        
        return response.translations[0].translated_text
    
    def _translate_ollama(self, text: str) -> str:
        """Ollamaで翻訳"""
        # Ollamaが利用可能か確認
        if not OLLAMA_AVAILABLE:
            raise Exception("Ollama Pythonパッケージがインストールされていません。'pip install ollama' を実行してください")
        
        # テキストが長すぎる場合は分割
        if len(text) > self.OLLAMA_MAX_INPUT_CHARS:
            return self._translate_ollama_long(text)
        
        prompt = f"""あなたは学術論文の翻訳者です。以下の英語テキストを日本語に翻訳してください。

【指示】
- である調で統一する
- ⟦記号⟧ は翻訳せず保持する
- 翻訳文のみを出力し、説明・前置き・後置きは一切不要

【英語テキスト】
{text}

【日本語訳】"""
        
        try:
            response = ollama.generate(
                model=self.ollama_model,
                prompt=prompt,
                options={
                    "temperature": self.ollama_temperature,
                    "num_ctx": self.OLLAMA_NUM_CTX,
                    "num_predict": self.OLLAMA_NUM_PREDICT,
                }
            )
            
            result = response['response'].strip()
            
            if not result:
                raise Exception("Ollamaが空の応答を返しました")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                raise Exception(
                    f"Ollamaサーバーに接続できません。\n"
                    f"  解決方法: 別のターミナルで 'ollama serve' を実行してください\n"
                    f"  詳細: {error_msg}"
                )
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                raise Exception(
                    f"モデル '{self.ollama_model}' が見つかりません。\n"
                    f"  解決方法: 'ollama pull {self.ollama_model}' を実行してください\n"
                    f"  または: 'ollama list' で利用可能なモデルを確認してください\n"
                    f"  詳細: {error_msg}"
                )
            elif "timeout" in error_msg.lower():
                raise Exception(
                    f"Ollamaがタイムアウトしました。\n"
                    f"  原因: テキストが長すぎるか、サーバーが過負荷です\n"
                    f"  詳細: {error_msg}"
                )
            else:
                raise Exception(f"Ollama翻訳エラー: {error_msg}")
    
    def _translate_ollama_long(self, text: str) -> str:
        """長いテキストをOllamaで翻訳（分割処理）"""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        translated_sentences = []
        current_batch: list[str] = []
        current_length = 0
        MAX_BATCH = self.OLLAMA_BATCH_CHARS   # 入力上限と連動した定数

        for sentence in sentences:
            sentence_length = len(sentence)

            # 1文だけで上限超過 → そのまま追加（分割不可）
            if sentence_length >= MAX_BATCH:
                if current_batch:
                    translated_sentences.append(
                        self._translate_ollama(' '.join(current_batch))
                    )
                    current_batch = []
                    current_length = 0
                # 長い文は翻訳を試みるが、再帰しない
                try:
                    translated_sentences.append(
                        self._translate_ollama_single(sentence)
                    )
                except Exception:
                    translated_sentences.append(sentence)  # 翻訳失敗はそのまま
                continue

            if current_length + sentence_length > MAX_BATCH and current_batch:
                translated_sentences.append(
                    self._translate_ollama(' '.join(current_batch))
                )
                current_batch = []
                current_length = 0

            current_batch.append(sentence)
            current_length += sentence_length

        if current_batch:
            translated_sentences.append(
                self._translate_ollama(' '.join(current_batch))
            )

        return ' '.join(translated_sentences)

    def _translate_ollama_single(self, text: str) -> str:
        """再帰しない単一Ollama翻訳（長文専用）"""
        response = ollama.generate(
            model=self.ollama_model,
            prompt=f"以下を日本語に翻訳してください（である調）:\n\n{text}\n\n日本語訳のみ出力:",
            options={
                "temperature": self.ollama_temperature,
                "num_ctx": self.OLLAMA_NUM_CTX,
                "num_predict": self.OLLAMA_NUM_PREDICT,
            }
        )
        return response['response'].strip()

    def get_usage(self) -> Dict[str, int]:
        """使用量を取得"""
        return self.usage.copy()


def test_translator():
    """テスト"""
    # サンプル用語辞書
    glossary = {
        "machine learning": "機械学習",
        "deep learning": "深層学習",
        "neural network": "ニューラルネットワーク",
        "complexity": "計算量"
    }
    
    # 翻訳エンジン初期化
    engine = TranslationEngine(glossary=glossary)
    
    # テストテキスト
    text = r"""
    We propose a novel machine learning approach with $O(n \log n)$ complexity.
    The deep learning model achieves high accuracy on the benchmark.
    See Figure 3 for details.
    """
    
    print("=" * 60)
    print("Original:")
    print(text)
    
    print("\n" + "=" * 60)
    print("Translating...")
    
    translated = engine.translate(text, show_stats=True)
    
    print("\n" + "=" * 60)
    print("Translated:")
    print(translated)
    
    print("\n" + "=" * 60)
    print("Usage:")
    for engine_name, chars in engine.get_usage().items():
        print(f"  {engine_name}: {chars} chars")


if __name__ == "__main__":
    test_translator()

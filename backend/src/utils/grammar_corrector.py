import language_tool_python
from typing import Optional
import logging
import threading  # 1. Import the threading module

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GrammarCorrector:
    def __init__(self) -> None:
        self.grammar_tool: Optional[language_tool_python.LanguageTool] = None
        self.lock = threading.Lock()  # 2. Initialize a lock for this instance
        self._initialize_grammar_tool()

    def _initialize_grammar_tool(self) -> None:
        """Initializes or reinitializes the LanguageTool instance."""
        if self.grammar_tool:
            try:
                self.grammar_tool.close()
                logging.info("Closed existing LanguageTool instance before reinitialization.")
            except Exception as e:
                logging.warning(f"Error closing existing LanguageTool instance: {e}")
        try:
            self.grammar_tool = language_tool_python.LanguageTool('en-US')
            logging.info("LanguageTool instance initialized successfully.")
        except Exception as e:
            self.grammar_tool = None
            logging.error(f"Failed to initialize LanguageTool: {e}")

    def correct(self, text: str) -> str:
        # 3. Use the lock to protect the entire method
        with self.lock:
            if not text:
                return ""

            if not self.grammar_tool:
                logging.warning("LanguageTool not initialized. Attempting to reinitialize.")
                self._initialize_grammar_tool()
                if not self.grammar_tool:
                    logging.error("Failed to reinitialize LanguageTool. Cannot correct grammar.")
                    return text # Return original text if tool cannot be initialized

            try:
                return self.grammar_tool.correct(text)
            except AttributeError as e:
                logging.error(f"AttributeError during grammar correction: {e}. Attempting to reinitialize LanguageTool.")
                self._initialize_grammar_tool()
                if self.grammar_tool:
                    try:
                        # Retry after reinitialization
                        return self.grammar_tool.correct(text)
                    except Exception as retry_e:
                        logging.error(f"Failed to correct grammar after reinitialization: {retry_e}. Returning original text.")
                        return text
                else:
                    logging.error("Failed to reinitialize LanguageTool after AttributeError. Cannot correct grammar.")
                    return text
            except Exception as e: # Catch other potential errors from language_tool_python
                logging.error(f"An unexpected error occurred during grammar correction: {e}. Returning original text.")
                return text

    def close(self) -> None:
        # Also protect the close method with the lock
        with self.lock:
            if self.grammar_tool:
                try:
                    self.grammar_tool.close()
                    logging.info("LanguageTool instance closed successfully.")
                except Exception as e:
                    logging.warning(f"Error during LanguageTool close: {e}. Tool might already be closed or in a bad state.")
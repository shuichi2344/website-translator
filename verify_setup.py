"""
Quick verification script to ensure all essential modules can be imported
Run this after cleanup to verify everything still works
"""

import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_import(module_name, description):
    """Try to import a module and report status"""
    try:
        __import__(module_name)
        print(f"OK {description}")
        return True
    except ImportError as e:
        print(f"FAIL {description} - {e}")
        return False

print("=" * 60)
print("Verifying Essential Modules")
print("=" * 60)

all_ok = True

# App modules
print("\nDesktop Application:")
all_ok &= test_import("app.router", "Router")
all_ok &= test_import("app.state", "State management")
all_ok &= test_import("app.components.theme", "Theme")
all_ok &= test_import("app.components.controls", "Controls")
all_ok &= test_import("app.views.login", "Login view")
all_ok &= test_import("app.views.home", "Home view")
all_ok &= test_import("app.views.profile", "Profile view")
all_ok &= test_import("app.views.preferences", "Preferences view")
all_ok &= test_import("app.views.onboarding", "Onboarding view")

# Database modules
print("\nDatabase:")
all_ok &= test_import("engine.database.auth_handler", "Auth handler")
all_ok &= test_import("engine.database.mysql_handler", "MySQL handler")
all_ok &= test_import("engine.database.rag_integration", "RAG integration")

# Search/Summarization modules
print("\nSearch & Summarization:")
all_ok &= test_import("engine.search.document_summariser_v6_gemini", "Document summarizer")
all_ok &= test_import("engine.search.speech_to_text", "Speech to text")

# Speech modules
print("\nSpeech Processing:")
all_ok &= test_import("engine.speech.main", "Speech main")
all_ok &= test_import("engine.speech.text_to_speech", "Text to speech")
all_ok &= test_import("engine.speech.speech_to_text", "Speech to text")
all_ok &= test_import("engine.speech.response_gen", "Response generation")
all_ok &= test_import("engine.speech.embedding", "Embeddings")
all_ok &= test_import("engine.speech.web_scraping", "Web scraping")

print("\n" + "=" * 60)
if all_ok:
    print("SUCCESS: All essential modules verified!")
    print("=" * 60)
    sys.exit(0)
else:
    print("ERROR: Some modules failed to import. Check errors above.")
    print("=" * 60)
    sys.exit(1)

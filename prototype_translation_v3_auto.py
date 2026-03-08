"""
Live Website Translation with Auto ChromeDriver Management
Automatically downloads and manages ChromeDriver
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from googletrans import Translator
import time

class LiveWebTranslator:
    def __init__(self, target_lang='en'):
        self.translator = Translator()
        self.target_lang = target_lang
        self.translated_cache = {}
        
    def translate_text(self, text):
        """Translate text with caching"""
        if not text or not text.strip():
            return text
        
        cache_key = text.strip()
        if cache_key in self.translated_cache:
            return self.translated_cache[cache_key]
        
        try:
            translated = self.translator.translate(text, dest=self.target_lang)
            result = translated.text
            self.translated_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def translate_page_content(self, driver):
        """Translate all visible text on the current page"""
        print("Translating page content...")
        
        try:
            # Get all elements with text (more comprehensive)
            elements = driver.find_elements(By.XPATH, "//*[not(self::script or self::style or self::noscript or self::code or self::pre)]")
            
            translated_count = 0
            total_elements = len(elements)
            
            print(f"Found {total_elements} elements to process...")
            
            for idx, element in enumerate(elements):
                try:
                    # Skip if already translated by our tool
                    if element.get_attribute('data-kiro-translated'):
                        continue
                    
                    # Get all text nodes and their content
                    text_nodes_info = driver.execute_script("""
                        const element = arguments[0];
                        const textNodes = [];
                        
                        for (let child of element.childNodes) {
                            if (child.nodeType === Node.TEXT_NODE) {
                                const text = child.textContent.trim();
                                if (text.length > 0) {
                                    textNodes.push({
                                        text: text,
                                        fullText: child.textContent  // Keep original with whitespace
                                    });
                                }
                            }
                        }
                        
                        return textNodes;
                    """, element)
                    
                    if text_nodes_info and len(text_nodes_info) > 0:
                        # Translate each text node
                        translations = []
                        needs_translation = False
                        
                        for node_info in text_nodes_info:
                            text = node_info['text']
                            translated = self.translate_text(text)
                            translations.append({
                                'original': node_info['fullText'],
                                'translated': translated,
                                'trimmed_original': text,
                                'changed': translated != text
                            })
                            if translated != text:
                                needs_translation = True
                        
                        if needs_translation:
                            # Replace all text nodes
                            success = driver.execute_script("""
                                const element = arguments[0];
                                const translations = arguments[1];
                                
                                let textNodeIndex = 0;
                                for (let child of element.childNodes) {
                                    if (child.nodeType === Node.TEXT_NODE) {
                                        const text = child.textContent.trim();
                                        if (text.length > 0 && textNodeIndex < translations.length) {
                                            const trans = translations[textNodeIndex];
                                            // Preserve leading/trailing whitespace
                                            const leadingSpace = child.textContent.match(/^\\s*/)[0];
                                            const trailingSpace = child.textContent.match(/\\s*$/)[0];
                                            child.textContent = leadingSpace + trans.translated + trailingSpace;
                                            textNodeIndex++;
                                        }
                                    }
                                }
                                
                                element.setAttribute('data-kiro-translated', 'true');
                                return true;
                            """, element, translations)
                            
                            if success:
                                translated_count += 1
                            
                            # Progress indicator
                            if translated_count % 25 == 0:
                                progress = (idx / total_elements) * 100
                                print(f"Progress: {progress:.0f}% - Translated {translated_count} elements...")
                            
                            # Small delay to avoid rate limiting
                            if translated_count % 10 == 0:
                                time.sleep(0.5)
                                
                except Exception as e:
                    # Continue on error for individual elements
                    continue
            
            print(f"✅ Translated {translated_count} elements")
            
            # Translate attributes
            self.translate_attributes(driver)
            
            # Force re-check for any missed elements
            self.translate_missed_elements(driver)
            
        except Exception as e:
            print(f"Error during translation: {e}")
    
    def translate_missed_elements(self, driver):
        """Second pass to catch any elements that might have been missed"""
        try:
            # Find elements with visible text that aren't marked as translated
            missed_elements = driver.execute_script("""
                const elements = [];
                const skipTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'PRE'];
                
                function hasVisibleText(element) {
                    if (skipTags.includes(element.tagName)) return false;
                    if (element.hasAttribute('data-kiro-translated')) return false;
                    
                    // Check if element has direct text content
                    for (let child of element.childNodes) {
                        if (child.nodeType === Node.TEXT_NODE) {
                            const text = child.textContent.trim();
                            if (text.length > 0) {
                                return true;
                            }
                        }
                    }
                    return false;
                }
                
                function walk(node) {
                    if (skipTags.includes(node.tagName)) return;
                    
                    if (hasVisibleText(node)) {
                        elements.push(node);
                    }
                    
                    for (let child of node.children) {
                        walk(child);
                    }
                }
                
                walk(document.body);
                return elements;
            """)
            
            if len(missed_elements) > 0:
                print(f"🔍 Found {len(missed_elements)} potentially missed elements, translating...")
                
                for element in missed_elements:
                    try:
                        # Get all text nodes
                        text_nodes_info = driver.execute_script("""
                            const element = arguments[0];
                            const textNodes = [];
                            
                            for (let child of element.childNodes) {
                                if (child.nodeType === Node.TEXT_NODE) {
                                    const text = child.textContent.trim();
                                    if (text.length > 0) {
                                        textNodes.push({
                                            text: text,
                                            fullText: child.textContent
                                        });
                                    }
                                }
                            }
                            
                            return textNodes;
                        """, element)
                        
                        if text_nodes_info and len(text_nodes_info) > 0:
                            translations = []
                            needs_translation = False
                            
                            for node_info in text_nodes_info:
                                text = node_info['text']
                                translated = self.translate_text(text)
                                translations.append({
                                    'original': node_info['fullText'],
                                    'translated': translated,
                                    'trimmed_original': text,
                                    'changed': translated != text
                                })
                                if translated != text:
                                    needs_translation = True
                            
                            if needs_translation:
                                driver.execute_script("""
                                    const element = arguments[0];
                                    const translations = arguments[1];
                                    
                                    let textNodeIndex = 0;
                                    for (let child of element.childNodes) {
                                        if (child.nodeType === Node.TEXT_NODE) {
                                            const text = child.textContent.trim();
                                            if (text.length > 0 && textNodeIndex < translations.length) {
                                                const trans = translations[textNodeIndex];
                                                const leadingSpace = child.textContent.match(/^\\s*/)[0];
                                                const trailingSpace = child.textContent.match(/\\s*$/)[0];
                                                child.textContent = leadingSpace + trans.translated + trailingSpace;
                                                textNodeIndex++;
                                            }
                                        }
                                    }
                                    
                                    element.setAttribute('data-kiro-translated', 'true');
                                """, element, translations)
                                
                                time.sleep(0.3)
                    except:
                        continue
                        
                print(f"✅ Second pass complete")
                
        except Exception as e:
            print(f"⚠️  Second pass error: {e}")
    
    def translate_attributes(self, driver):
        """Translate common attributes"""
        attrs = ['alt', 'title', 'placeholder', 'aria-label']
        
        for attr in attrs:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[@{attr}]")
                for element in elements:
                    try:
                        original = element.get_attribute(attr)
                        if original and original.strip():
                            translated = self.translate_text(original)
                            driver.execute_script(
                                f"arguments[0].setAttribute('{attr}', arguments[1]);",
                                element, translated
                            )
                    except:
                        continue
            except:
                continue
    
    def start_translation_session(self, url):
        """Start a live browser session with translation"""
        print("=" * 60)
        print("Live Website Translation")
        print("=" * 60)
        print(f"\nStarting browser for: {url}")
        
        # Try to use webdriver-manager if available
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            print("Using webdriver-manager for automatic ChromeDriver setup...")
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            driver = webdriver.Chrome(service=service, options=options)
        except ImportError:
            print("webdriver-manager not found, using default ChromeDriver...")
            print("Install with: pip install webdriver-manager")
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            driver = webdriver.Chrome(options=options)
        
        try:
            # Load website
            print("Loading website...")
            driver.get(url)
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # Wait for dynamic content
            
            # Translate
            self.translate_page_content(driver)
            
            print("\n" + "=" * 60)
            print("✅ Translation complete!")
            print("\nYou can now:")
            print("  • Click links to navigate (new pages auto-translate)")
            print("  • Use dropdowns and menus")
            print("  • Fill forms and interact normally")
            print("\n💡 Tip: If you see untranslated text after interactions,")
            print("   wait a moment - dynamic content translates automatically")
            print("\nPress Ctrl+C in terminal to close browser")
            print("=" * 60)
            
            # Monitor for navigation and dynamic content
            current_url = driver.current_url
            last_translation_time = time.time()
            
            while True:
                time.sleep(2)
                
                # Check if URL changed (navigation)
                new_url = driver.current_url
                if new_url != current_url:
                    print(f"\n📄 New page detected: {new_url}")
                    time.sleep(2)  # Wait for page load
                    self.translate_page_content(driver)
                    current_url = new_url
                    last_translation_time = time.time()
                
                # Periodically check for new dynamic content (every 10 seconds)
                elif time.time() - last_translation_time > 10:
                    # Check for untranslated elements
                    untranslated_count = driver.execute_script("""
                        const skipTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'PRE'];
                        let count = 0;
                        
                        function walk(node) {
                            if (skipTags.includes(node.tagName)) return;
                            if (node.hasAttribute('data-kiro-translated')) return;
                            
                            for (let child of node.childNodes) {
                                if (child.nodeType === Node.TEXT_NODE) {
                                    const text = child.textContent.trim();
                                    if (text.length > 0) {
                                        count++;
                                        return;
                                    }
                                }
                            }
                            
                            for (let child of node.children) {
                                walk(child);
                            }
                        }
                        
                        walk(document.body);
                        return count;
                    """)
                    
                    if untranslated_count > 5:  # Only translate if significant new content
                        print(f"\n🔄 Detected {untranslated_count} new elements, translating...")
                        self.translate_missed_elements(driver)
                    
                    last_translation_time = time.time()
                    
        except KeyboardInterrupt:
            print("\n\n👋 Closing browser...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nMake sure ChromeDriver is installed:")
            print("  pip install webdriver-manager")
        finally:
            driver.quit()


def main():
    print("=" * 60)
    print("🌐 Live Website Translation Tool")
    print("=" * 60)
    
    # Get URL
    url = input("\nEnter website URL: ").strip()
    if not url:
        print("No URL provided.")
        return
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get target language
    print("\nCommon language codes:")
    print("  en - English")
    print("  zh-cn - Chinese (Simplified)")
    print("  es - Spanish")
    print("  fr - French")
    print("  de - German")
    print("  ja - Japanese")
    print("  ko - Korean")
    print("  hi - Hindi")
    print("  ar - Arabic")
    
    target_lang = input("\nEnter target language code (default: en): ").strip() or 'en'
    
    # Start
    translator = LiveWebTranslator(target_lang=target_lang)
    translator.start_translation_session(url)


if __name__ == "__main__":
    main()

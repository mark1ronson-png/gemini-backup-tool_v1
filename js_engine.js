// Gemini Chat Backup JS Engine v2.0 FINAL
// Dizajniran za Python Playwright integraciju
(function() {
    'use strict';
    
    // Konfiguracija (može biti overridana iz Pythona)
    const CONFIG = {
        WAIT_TIME_SLOW: 1000,
        WAIT_TIME_FAST: 400,
        MAX_RETRIES: 3,
        MAX_MESSAGES: 10000,
        EXPORT_FORMAT: 'markdown' // 'markdown', 'json', 'both'
    };
    
    // Stanje
    const STATE = {
        processedMessages: new Set(),
        allMessages: [],
        retryCount: 0,
        lastMessageCount: 0,
        currentWaitTime: CONFIG.WAIT_TIME_FAST,
        isRunning: false,
        status: 'idle'
    };
    
    // Logging za Python komunikaciju
    function log(level, message, data = null) {
        const output = {
            timestamp: new Date().toISOString(),
            level: level,
            message: message,
            data: data,
            messageCount: STATE.allMessages.length,
            retryCount: STATE.retryCount
        };
        console.log(`[GEMINI_BACKUP] ${JSON.stringify(output)}`);
    }
    
    // Hash za deduplikaciju
    function createMessageHash(role, content) {
        return `${role}|${content.substring(0, 150)}`;
    }
    
    // Pronađi scrollabilni kontejner
    function findScrollableContainer() {
        const sampleMessage = document.querySelector('user-query') ||
                            document.querySelector('[data-message-role="user"]') ||
                            document.querySelector('.user-query');
        
        if (!sampleMessage) {
            throw new Error('NO_USER_QUERY_FOUND');
        }
        
        let element = sampleMessage;
        let attempts = 0;
        
        while (element && element !== document.body && attempts < 15) {
            const style = window.getComputedStyle(element);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                element.scrollHeight > element.clientHeight) {
                return element;
            }
            element = element.parentElement;
            attempts++;
        }
        
        // Fallback
        const allElements = document.querySelectorAll('*');
        for (const el of allElements) {
            const style = window.getComputedStyle(el);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                el.scrollHeight > el.clientHeight &&
                (el.querySelector('user-query') || el.querySelector('model-response'))) {
                return el;
            }
        }
        
        throw new Error('NO_SCROLLABLE_CONTAINER');
    }
    
    // Ekstrakcija Markdowna iz elementa
    function extractMarkdownFromElement(element) {
        if (!element) return '';
        
        const markdownEl = element.querySelector('.markdown');
        const targetEl = markdownEl || element;
        const clone = targetEl.cloneNode(true);
        
        processCodeBlocks(clone);
        processImages(clone);
        processLatex(clone);
        processTables(clone);
        
        return extractFormattedText(clone);
    }
    
    function processCodeBlocks(container) {
        const codeBlocks = container.querySelectorAll('pre');
        codeBlocks.forEach(pre => {
            const code = pre.querySelector('code');
            let language = '';
            let codeText = '';
            
            if (code) {
                const classes = code.className.split(' ');
                language = classes.find(c => c.startsWith('language-'))?.replace('language-', '') || '';
                codeText = code.textContent || code.innerText;
            } else {
                codeText = pre.textContent || pre.innerText;
            }
            
            const mdCodeBlock = document.createElement('div');
            mdCodeBlock.textContent = '```' + language + '\n' + codeText.trim() + '\n```';
            mdCodeBlock.setAttribute('data-gemini-code', 'true');
            pre.parentNode?.replaceChild(mdCodeBlock, pre);
        });
    }
    
    function processImages(container) {
        const images = container.querySelectorAll('img');
        images.forEach(img => {
            const src = img.src || img.getAttribute('data-src') || img.getAttribute('srcset')?.split(',')[0]?.trim()?.split(' ')[0] || '';
            const alt = img.alt || 'slika';
            
            if (src && !src.startsWith('data:')) {
                const mdImage = document.createElement('span');
                mdImage.textContent = '![' + alt + '](' + src + ')';
                mdImage.setAttribute('data-gemini-image', 'true');
                img.parentNode?.replaceChild(mdImage, img);
            }
        });
    }
    
    function processLatex(container) {
        const mathElements = container.querySelectorAll(
            'math, [class*="math"], [class*="katex"], [class*="latex"], ' +
            'span[class*="MathJax"], .math-inline, .math-display, [data-latex]'
        );
        
        mathElements.forEach(math => {
            const latex = math.getAttribute('data-latex') ||
                         math.textContent?.trim() || '';
            
            if (latex) {
                const isBlock = math.classList.contains('math-display') ||
                               math.tagName === 'MATH' ||
                               math.getAttribute('data-display') === 'true';
                
                const mdLatex = document.createElement('span');
                mdLatex.textContent = isBlock ? '\n$$\n' + latex + '\n$$\n' : '$' + latex + '$';
                mdLatex.setAttribute('data-gemini-latex', 'true');
                math.parentNode?.replaceChild(mdLatex, math);
            }
        });
        
        // Custom math elements
        const customMath = container.querySelectorAll('[math], [latex]');
        customMath.forEach(el => {
            const formula = el.getAttribute('math') || el.getAttribute('latex') || el.textContent?.trim();
            if (formula) {
                const mdLatex = document.createElement('span');
                mdLatex.textContent = '$' + formula + '$';
                mdLatex.setAttribute('data-gemini-latex', 'true');
                el.parentNode?.replaceChild(mdLatex, el);
            }
        });
    }
    
    function processTables(container) {
        const tables = container.querySelectorAll('table');
        tables.forEach(table => {
            let mdTable = '\n';
            const rows = table.querySelectorAll('tr');
            
            rows.forEach((row, rowIndex) => {
                const cells = row.querySelectorAll('td, th');
                const cellContents = Array.from(cells).map(cell =>
                    cell.textContent?.trim().replace(/\|/g, '\\|') || ''
                );
                
                mdTable += '| ' + cellContents.join(' | ') + ' |\n';
                
                if (rowIndex === 0) {
                    mdTable += '| ' + cellContents.map(() => '---').join(' | ') + ' |\n';
                }
            });
            
            const mdTableEl = document.createElement('div');
            mdTableEl.textContent = mdTable;
            mdTableEl.setAttribute('data-gemini-table', 'true');
            table.parentNode?.replaceChild(mdTableEl, table);
        });
    }
    
    function extractFormattedText(container) {
        let text = '';
        
        function processNode(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                text += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                const hasSpecialMarkup = node.hasAttribute('data-gemini-code') ||
                                       node.hasAttribute('data-gemini-image') ||
                                       node.hasAttribute('data-gemini-latex') ||
                                       node.hasAttribute('data-gemini-table');
                
                if (hasSpecialMarkup) {
                    text += node.textContent;
                    return;
                }
                
                const tag = node.tagName.toLowerCase();
                
                switch(tag) {
                    case 'h1': text += '\n# '; break;
                    case 'h2': text += '\n## '; break;
                    case 'h3': text += '\n### '; break;
                    case 'h4': text += '\n#### '; break;
                    case 'h5': text += '\n##### '; break;
                    case 'h6': text += '\n###### '; break;
                    case 'strong': case 'b': text += '**'; break;
                    case 'em': case 'i': text += '*'; break;
                    case 'del': case 's': text += '~~'; break;
                    case 'a': break; // Handled after children
                    case 'ul': case 'ol': text += '\n'; break;
                    case 'li': text += '- '; break;
                    case 'br': text += '\n'; break;
                    case 'p': if (node.previousSibling) text += '\n\n'; break;
                    case 'blockquote': text += '> '; break;
                    case 'hr': text += '\n---\n'; break;
                }
                
                node.childNodes.forEach(child => processNode(child));
                
                switch(tag) {
                    case 'strong': case 'b': text += '**'; break;
                    case 'em': case 'i': text += '*'; break;
                    case 'del': case 's': text += '~~'; break;
                    case 'a':
                        const href = node.getAttribute('href');
                        if (href) text += '[' + node.textContent + '](' + href + ')';
                        break;
                    case 'h1': case 'h2': case 'h3': case 'h4': case 'h5': case 'h6':
                        text += '\n'; break;
                }
            }
        }
        
        processNode(container);
        
        return text
            .replace(/\n{3,}/g, '\n\n')
            .replace(/[ \t]+/g, ' ')
            .replace(/\n +/g, '\n')
            .trim();
    }
    
    function extractMessageContent(element) {
        if (!element) return '';
        return extractMarkdownFromElement(element);
    }
    
    // Skupljanje poruka
    function scrapeCurrentMessages() {
        const userQueries = document.querySelectorAll('user-query');
        const modelResponses = document.querySelectorAll('model-response');
        const messages = [];
        
        userQueries.forEach(el => {
            const content = extractMessageContent(el).trim();
            if (content && content.length > 0) {
                messages.push({
                    role: 'user',
                    content: content,
                    element: el
                });
            }
        });
        
        modelResponses.forEach(el => {
            const content = extractMessageContent(el).trim();
            if (content && content.length > 0) {
                messages.push({
                    role: 'assistant',
                    content: content,
                    element: el
                });
            }
        });
        
        return messages;
    }
    
    function processMessages(messages) {
        let newMessagesAdded = false;
        
        messages.forEach(msg => {
            const hash = createMessageHash(msg.role, msg.content);
            if (!STATE.processedMessages.has(hash)) {
                STATE.processedMessages.add(hash);
                STATE.allMessages.push(msg);
                newMessagesAdded = true;
            }
        });
        
        // Kronološko sortiranje prema DOM poziciji
        STATE.allMessages.sort((a, b) => {
            const position = a.element.compareDocumentPosition(b.element);
            if (position & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
            if (position & Node.DOCUMENT_POSITION_PRECEDING) return 1;
            return 0;
        });
        
        return newMessagesAdded;
    }
    
    // Detekcija naslova
    function getChatTitle() {
        // Strategija 1: H1
        const h1 = document.querySelector('h1[class*="title"], h1[class*="heading"], h1[class*="chat"], h1');
        if (h1 && h1.textContent.trim().length > 0) {
            return h1.textContent.trim();
        }
        
        // Strategija 2: Aktivni sidebar item
        const active = document.querySelector(
            '[class*="active"][class*="chat"], [class*="selected"][class*="chat"], ' +
            '[aria-current="page"], .chat-list-item.active'
        );
        if (active && active.textContent.trim().length > 0) {
            return active.textContent.trim();
        }
        
        // Strategija 3: Title (bez "Gemini")
        const title = document.querySelector('title');
        if (title && !title.textContent.includes('Gemini')) {
            return title.textContent.replace(' - Gemini', '').trim();
        }
        
        return 'untitled-chat';
    }
    
    // Generiranje outputa
    function generateOutput(format) {
        const chatTitle = getChatTitle();
        let result = {};
        
        if (format === 'markdown' || format === 'both') {
            let markdown = '# ' + chatTitle + '\n\n';
            markdown += '*Backup kreiran: ' + new Date().toLocaleString() + '*\n\n';
            markdown += '*Ukupno poruka: ' + STATE.allMessages.length + '*\n\n';
            markdown += '---\n\n';
            
            STATE.allMessages.forEach((msg, index) => {
                if (msg.role === 'user') {
                    markdown += '## 👤 Vi\n\n' + msg.content + '\n\n';
                } else {
                    markdown += '## 🤖 Gemini\n\n' + msg.content + '\n\n';
                }
                if (index < STATE.allMessages.length - 1) {
                    markdown += '---\n\n';
                }
            });
            
            markdown += '\n\n---\n\n';
            markdown += '*Backup generiran s Gemini Chat Backup Tool | ' + new Date().toISOString() + '*';
            
            result.markdown = markdown;
        }
        
        if (format === 'json' || format === 'both') {
            const messagesForJson = STATE.allMessages.map(msg => ({
                role: msg.role,
                content: msg.content,
                timestamp: new Date().toISOString()
            }));
            
            result.json = {
                title: chatTitle,
                exportDate: new Date().toISOString(),
                totalMessages: messagesForJson.length,
                messages: messagesForJson
            };
        }
        
        return result;
    }
    
    // Dohvati sve chat linkove iz sidebar-a
    function getSidebarChats() {
        const chatLinks = [];
        
        // Traži sve linkove u sidebaru
        const sidebar = document.querySelector(
            '[class*="sidebar"], [class*="side-nav"], [class*="drawer"], [class*="nav"]'
        );
        
        if (sidebar) {
            const links = sidebar.querySelectorAll('a[href*="/app/"]');
            links.forEach(link => {
                const href = link.href;
                const title = link.textContent.trim();
                if (href && title) {
                    chatLinks.push({
                        url: href,
                        title: title
                    });
                }
            });
        }
        
        // Fallback: traži sve Gemini chat linkove na stranici
        if (chatLinks.length === 0) {
            const allLinks = document.querySelectorAll('a[href*="gemini.google.com/app/"]');
            allLinks.forEach(link => {
                const href = link.href;
                const title = link.textContent.trim() || link.getAttribute('aria-label') || 'Unknown Chat';
                if (href && !chatLinks.find(c => c.url === href)) {
                    chatLinks.push({ url: href, title: title });
                }
            });
        }
        
        return chatLinks;
    }
    
    // Glavna funkcija backupa
    async function performBackup(scrollContainer = null) {
        if (STATE.isRunning) {
            log('warn', 'Backup already running');
            return null;
        }
        
        STATE.isRunning = true;
        STATE.status = 'running';
        STATE.allMessages = [];
        STATE.processedMessages = new Set();
        STATE.retryCount = 0;
        STATE.lastMessageCount = 0;
        STATE.currentWaitTime = CONFIG.WAIT_TIME_FAST;
        
        try {
            log('info', 'Starting backup process');
            
            // Pronađi kontejner
            const container = scrollContainer || findScrollableContainer();
            log('info', 'Scroll container found');
            
            // Scroll petlja
            while (STATE.retryCount < CONFIG.MAX_RETRIES) {
                const wasAtTop = container.scrollTop === 0;
                container.scrollTop = 0;
                container.dispatchEvent(new Event('scroll', { bubbles: true }));
                
                await new Promise(resolve => setTimeout(resolve, STATE.currentWaitTime));
                
                const currentMessages = scrapeCurrentMessages();
                const newMessagesAdded = processMessages(currentMessages);
                
                if (newMessagesAdded && currentMessages.length > STATE.lastMessageCount) {
                    STATE.currentWaitTime = CONFIG.WAIT_TIME_FAST;
                    STATE.retryCount = 0;
                    log('info', 'Messages found', { new: STATE.allMessages.length });
                } else {
                    STATE.currentWaitTime = CONFIG.WAIT_TIME_SLOW;
                    STATE.retryCount++;
                    log('debug', 'Retry', { retry: STATE.retryCount });
                }
                
                STATE.lastMessageCount = currentMessages.length;
                
                if (wasAtTop && !newMessagesAdded) {
                    log('info', 'Reached top');
                    break;
                }
                
                if (STATE.allMessages.length >= CONFIG.MAX_MESSAGES) {
                    log('warn', 'Max messages limit reached');
                    break;
                }
            }
            
            if (STATE.allMessages.length === 0) {
                throw new Error('NO_MESSAGES_FOUND');
            }
            
            // Generiraj output
            const output = generateOutput(CONFIG.EXPORT_FORMAT);
            log('success', 'Backup complete', {
                totalMessages: STATE.allMessages.length,
                format: CONFIG.EXPORT_FORMAT
            });
            
            STATE.status = 'completed';
            return output;
            
        } catch (error) {
            log('error', error.message);
            STATE.status = 'error';
            throw error;
        } finally {
            STATE.isRunning = false;
        }
    }
    
    // Expose API
    window.GeminiBackup = {
        performBackup: performBackup,
        getSidebarChats: getSidebarChats,
        getState: () => STATE,
        getConfig: () => CONFIG,
        updateConfig: (newConfig) => Object.assign(CONFIG, newConfig),
        getChatTitle: getChatTitle
    };
    
    log('info', 'JS Engine loaded and ready');
})();
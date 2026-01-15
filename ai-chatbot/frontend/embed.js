/**
 * UzSWLU AI Chatbot Widget
 * Embed this script on uzswlu.uz website
 * 
 * Usage:
 * <script src="https://chatbot.uzswlu.uz/embed.js"></script>
 */

(function () {
     'use strict';

     // Configuration
     const CONFIG = {
          chatbotUrl: window.UZSWLU_CHATBOT_URL || 'https://chatbot.uzswlu.uz/widget.html',
          position: 'bottom-right', // bottom-right, bottom-left
          theme: 'light', // light, dark
          language: 'uz', // uz, ru, en
          zIndex: 999999
     };

     // Create widget HTML
     function createWidget() {
          const widgetHTML = `
            <div id="uzswlu-chatbot-widget" style="
                position: fixed;
                ${CONFIG.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
                ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                z-index: ${CONFIG.zIndex};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            ">
                <!-- Chat Toggle Button -->
                <button id="uzswlu-chat-toggle" style="
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                " onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <!-- Notification Badge -->
                    <span id="uzswlu-chat-badge" style="
                        position: absolute;
                        top: 5px;
                        right: 5px;
                        width: 12px;
                        height: 12px;
                        background: #ef4444;
                        border-radius: 50%;
                        border: 2px solid white;
                        display: none;
                    "></span>
                </button>

                <!-- Chat Container -->
                <div id="uzswlu-chat-container" style="
                    position: fixed;
                    ${CONFIG.position.includes('bottom') ? 'bottom: 90px;' : 'top: 90px;'}
                    ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                    width: 400px;
                    height: 600px;
                    max-width: calc(100vw - 40px);
                    max-height: calc(100vh - 120px);
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                    transform: scale(0.95);
                    opacity: 0;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                ">
                    <!-- Header -->
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 16px 20px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="
                                width: 36px;
                                height: 36px;
                                background: rgba(255, 255, 255, 0.2);
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            ">💠</div>
                            <div>
                                <div style="font-weight: 600; font-size: 15px;">UzSWLU AI</div>
                                <div style="font-size: 12px; opacity: 0.9;">Online</div>
                            </div>
                        </div>
                        <button id="uzswlu-chat-close" style="
                            background: transparent;
                            border: none;
                            color: white;
                            cursor: pointer;
                            font-size: 24px;
                            padding: 0;
                            width: 32px;
                            height: 32px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border-radius: 50%;
                            transition: background 0.2s;
                        " onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='transparent'">×</button>
                    </div>

                    <!-- Iframe -->
                    <iframe 
                        id="uzswlu-chat-iframe"
                        src="${CONFIG.chatbotUrl}"
                        style="
                            flex: 1;
                            border: none;
                            width: 100%;
                            height: 100%;
                        "
                        allow="microphone; camera"
                        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                    ></iframe>
                </div>
            </div>
        `;

          // Inject widget into page
          const container = document.createElement('div');
          container.innerHTML = widgetHTML;
          document.body.appendChild(container.firstElementChild);
     }

     // Toggle chat visibility
     function toggleChat() {
          const container = document.getElementById('uzswlu-chat-container');
          const button = document.getElementById('uzswlu-chat-toggle');
          const badge = document.getElementById('uzswlu-chat-badge');

          if (container.style.display === 'none' || !container.style.display) {
               // Open chat
               container.style.display = 'flex';
               setTimeout(() => {
                    container.style.transform = 'scale(1)';
                    container.style.opacity = '1';
               }, 10);
               button.style.transform = 'rotate(90deg)';
               badge.style.display = 'none';

               // Track analytics
               if (window.gtag) {
                    gtag('event', 'chatbot_opened', {
                         event_category: 'engagement',
                         event_label: 'UzSWLU Chatbot'
                    });
               }
          } else {
               // Close chat
               container.style.transform = 'scale(0.95)';
               container.style.opacity = '0';
               setTimeout(() => {
                    container.style.display = 'none';
               }, 300);
               button.style.transform = 'rotate(0deg)';
          }
     }

     // Initialize widget
     function init() {
          // Wait for DOM to be ready
          if (document.readyState === 'loading') {
               document.addEventListener('DOMContentLoaded', createWidget);
          } else {
               createWidget();
          }

          // Add event listeners after widget is created
          setTimeout(() => {
               const toggleBtn = document.getElementById('uzswlu-chat-toggle');
               const closeBtn = document.getElementById('uzswlu-chat-close');

               if (toggleBtn) {
                    toggleBtn.addEventListener('click', toggleChat);
               }

               if (closeBtn) {
                    closeBtn.addEventListener('click', toggleChat);
               }

               // Show notification badge after 5 seconds
               setTimeout(() => {
                    const badge = document.getElementById('uzswlu-chat-badge');
                    if (badge) {
                         badge.style.display = 'block';
                    }
               }, 5000);
          }, 100);
     }

     // Start initialization
     init();

     // Expose API for external control
     window.UzSWLUChatbot = {
          open: function () {
               const container = document.getElementById('uzswlu-chat-container');
               if (container && container.style.display === 'none') {
                    toggleChat();
               }
          },
          close: function () {
               const container = document.getElementById('uzswlu-chat-container');
               if (container && container.style.display !== 'none') {
                    toggleChat();
               }
          },
          toggle: toggleChat
     };

})();

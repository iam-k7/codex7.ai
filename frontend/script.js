document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const API_BASE_URL =
        window.location.hostname === 'localhost'
            ? 'http://localhost:8000'
            : '';

    initParticles();

    // --- State Management ---
    // --- State Management ---
    let currentCaptions = [
        { start: 0.0, end: 0.4, text: "If you are watching" },
        { start: 0.5, end: 1.4, text: "all this," },
        { start: 2.0, end: 3.0, text: "you can watch this" },
        { start: 3.1, end: 3.4, text: "video." },
        { start: 3.5, end: 3.9, text: "If you are enjoying," }
    ];
    let originalAiCaptions = JSON.parse(JSON.stringify(currentCaptions));
    let lastActiveSegmentIndex = -1;
    let isPlaying = false;
    let animationFrameId = null;

    // --- Toast System ---
    const showToast = (message, type = 'success') => {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
            <span class="toast-msg">${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 400);
            }, 3000);
        }, 100);
    };

    // --- DOM Elements ---
    const videoUpload = document.getElementById('video-upload');
    const mainVideo = document.getElementById('main-video');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const playIcon = document.getElementById('play-icon');
    const pauseIcon = document.getElementById('pause-icon');
    const videoTimeline = document.getElementById('video-timeline');
    const timeDisplay = document.getElementById('time-display');
    const captionOverlay = document.getElementById('caption-overlay');
    const captionTextContent = document.getElementById('caption-text-content');
    const transcriptList = document.getElementById('transcript-list');
    const generateBtn = document.getElementById('generate-btn');
    const processingStatus = document.getElementById('processing-status');
    const snapTimingBtn = document.getElementById('snap-timing-btn');
    const aiMessage = document.getElementById('ai-message');
    const uploadZone = document.getElementById('upload-zone');

    // Customization elements
    const fontSelector = document.getElementById('font-selector');
    const fontSizeSlider = document.getElementById('font-size-slider');
    const fontSizeValue = document.getElementById('font-size-value');
    const colorPicker = document.getElementById('color-picker');
    const colorSwatches = document.querySelectorAll('.color-swatch');
    const animationSelector = document.getElementById('animation-selector');
    const posButtons = document.querySelectorAll('.pos-btn');

    // Tab elements
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Mobile Drawer elements
    const mobilePanelToggle = document.getElementById('mobile-panel-toggle');
    const closePanelBtn = document.getElementById('close-panel-btn');
    const controlPanel = document.getElementById('control-panel');
    const drawerOverlay = document.getElementById('drawer-overlay');

    function toggleMobilePanel(show) {
        if (controlPanel) controlPanel.classList.toggle('show', show);
        if (drawerOverlay) drawerOverlay.classList.toggle('show', show);
    }

    mobilePanelToggle?.addEventListener('click', () => toggleMobilePanel(true));
    closePanelBtn?.addEventListener('click', () => toggleMobilePanel(false));
    drawerOverlay?.addEventListener('click', () => toggleMobilePanel(false));

    // Close panel when a tab is clicked on mobile (optional but useful)
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                // Keep it open if you want to switch tabs, usually better to stay open
                // toggleMobilePanel(false); 
            }
        });
    });

    // --- Session Management ---
    const userEmail = localStorage.getItem('codex7_email');
    const userNameSaved = localStorage.getItem('codex7_name');

    // Check current page
    const isLoginPage = !!document.getElementById('login-container');
    const isEditorPage = !!document.querySelector('.editor-body');

    if (isLoginPage && userEmail) {
        window.location.href = '/editor.html';
        return;
    }

    if (isEditorPage && !userEmail) {
        window.location.href = '/index.html';
        return;
    }

    if (aiMessage) {
        const displayName = userNameSaved || 'Creator';
        aiMessage.innerHTML = `Welcome to <strong>codex7.ai</strong> — Built by Kesavan<br>Hello, ${displayName}! Ready to make your video viral? 🚀`;
    }

    // --- User Profile & Dropdown ---
    function initProfile() {
        const trigger = document.getElementById('profile-trigger');
        const dropdown = document.getElementById('profile-dropdown');
        const nameDisplay = document.getElementById('user-display-name');
        const initials = document.getElementById('avatar-initials');
        const logoutTrigger = document.getElementById('logout-trigger');

        if (!userNameSaved) return;

        // Display FIRST NAME only, Capitalized
        const firstName = userNameSaved.split(' ')[0];
        if (nameDisplay) {
            nameDisplay.textContent = firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
        }

        // Set Initial letter
        if (initials) {
            initials.textContent = firstName.charAt(0).toUpperCase();
        }



        // Toggle Dropdown
        if (trigger && dropdown) {
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('show');
                trigger.classList.toggle('active');
            });

            // Close on outside click
            document.addEventListener('click', () => {
                dropdown.classList.remove('show');
                trigger.classList.remove('active');
            });
        }

        // Logout within dropdown
        if (logoutTrigger) {
            logoutTrigger.addEventListener('click', () => {
                if (confirm("Are you sure you want to logout?")) {
                    localStorage.clear();
                    window.location.href = '/index.html';
                }
            });
        }
    }
    if (isEditorPage) initProfile();

    // --- History Loading ---
    async function loadHistory() {
        const historyList = document.getElementById('history-list');
        if (!historyList || !userEmail) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/history?email=${userEmail}`);
            const history = await response.json();

            if (history && history.length > 0) {
                historyList.innerHTML = '';
                history.reverse().forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'history-item';
                    div.style.cssText = 'padding: 12px; border-radius: 12px; background: white; border: 1px solid #efefef; margin-bottom: 8px; cursor: pointer; transition: all 0.2s;';
                    div.innerHTML = `
                        <div style="font-weight: 700; font-size: 0.8rem; margin-bottom: 4px;">${item.video_name || 'Untitled Project'}</div>
                        <div style="font-size: 0.7rem; color: #999;">${new Date(item.timestamp).toLocaleDateString()}</div>
                    `;
                    div.onmouseover = () => div.style.borderColor = '#FF4D4F';
                    div.onmouseout = () => div.style.borderColor = '#efefef';
                    historyList.appendChild(div);
                });
            }
        } catch (err) {
            console.error("Failed to load history", err);
        }
    }
    if (isEditorPage) {
        loadHistory();
        renderTranscript(); // Render initial demo state
    }

    // --- Country Population ---
    const countrySelect = document.getElementById('country');
    if (countrySelect) {
        const countries = [
            "United States", "India", "United Kingdom", "Canada", "Australia",
            "Germany", "France", "Japan", "Brazil", "Singapore", "United Arab Emirates",
            "Mexico", "Italy", "Spain", "Netherlands", "Switzerland", "South Korea"
        ].sort();

        countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = country;
            countrySelect.appendChild(option);
        });
    }

    // --- Login Logic ---
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const country = document.getElementById('country').value;

            try {
                // Mocking the backend call for now, but following the flow
                await fetch(`${API_BASE_URL}/api/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, country })
                });

                localStorage.setItem('codex7_email', email);
                localStorage.setItem('codex7_name', name);
                window.location.href = 'editor.html';
            } catch (err) {
                console.error("Login fallback", err);
                localStorage.setItem('codex7_email', email);
                localStorage.setItem('codex7_name', name);
                window.location.href = 'editor.html';
            }
        });
    }

    // --- Tab Switching ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
        });
    });

    // --- Video Upload & Timeline ---
    if (uploadZone) {
        uploadZone.addEventListener('click', () => videoUpload.click());

        videoUpload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Duration Check (Max 60 Seconds)
                const tempVideo = document.createElement('video');
                tempVideo.preload = 'metadata';
                tempVideo.onloadedmetadata = () => {
                    if (tempVideo.duration > 61) {
                        alert("Please upload a video shorter than 60 seconds.");
                        videoUpload.value = '';
                        return;
                    }

                    const url = URL.createObjectURL(file);
                    mainVideo.src = url;
                    mainVideo.hidden = false;
                    uploadZone.classList.add('hidden');
                    generateBtn.classList.remove('hidden');
                    generateBtn.disabled = false;

                    mainVideo.onloadedmetadata = () => {
                        videoTimeline.max = mainVideo.duration;
                        updateTimeDisplay();
                    };
                };
                tempVideo.src = URL.createObjectURL(file);
            }
        });
    }

    // --- Playback Control ---
    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', togglePlayback);
    }

    function togglePlayback() {
        if (mainVideo.paused) {
            mainVideo.play();
            playIcon?.classList.add('hidden');
            pauseIcon?.classList.remove('hidden');
            isPlaying = true;
            startSyncLoop();
        } else {
            mainVideo.pause();
            playIcon?.classList.remove('hidden');
            pauseIcon?.classList.add('hidden');
            isPlaying = false;
            stopSyncLoop();
        }
    }

    if (videoTimeline) {
        videoTimeline.addEventListener('input', () => {
            mainVideo.currentTime = videoTimeline.value;
            updateTimeDisplay();
            syncCaptions();
        });
    }

    function updateTimeDisplay() {
        if (!timeDisplay) return;
        const current = formatTime(mainVideo.currentTime);
        const duration = formatTime(mainVideo.duration || 0);
        timeDisplay.textContent = `${current} / ${duration}`;
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // --- Synchronization Logic ---
    function startSyncLoop() {
        if (!isPlaying) return;
        syncCaptions();
        if (videoTimeline) videoTimeline.value = mainVideo.currentTime;
        updateTimeDisplay();
        animationFrameId = requestAnimationFrame(startSyncLoop);
    }

    function stopSyncLoop() {
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
    }

    function syncCaptions() {
        if (!currentCaptions || !currentCaptions.length) return;

        const currentTime = mainVideo.currentTime;
        let activeSegmentIndex = -1;

        for (let i = 0; i < currentCaptions.length; i++) {
            if (currentTime >= currentCaptions[i].start && currentTime <= currentCaptions[i].end) {
                activeSegmentIndex = i;
                break;
            }
        }

        if (activeSegmentIndex !== lastActiveSegmentIndex) {
            if (activeSegmentIndex !== -1) {
                const segment = currentCaptions[activeSegmentIndex];
                const displayText = segment.text || segment.word || ""; // Fallback for safety

                if (captionTextContent) {
                    captionTextContent.textContent = displayText;

                    // Apply highlight color if active
                    const activeColor = document.querySelector('.color-swatch.active')?.dataset.color || '#ffffff';
                    captionTextContent.style.color = activeColor;

                    captionOverlay?.classList.remove('hidden');

                    // Apply entry animation
                    const anim = animationSelector?.value || 'pop';
                    captionTextContent.className = 'caption-word';
                    if (anim !== 'none') {
                        captionTextContent.classList.add(`caption-${anim}`);
                    }
                }
                highlightSegment(activeSegmentIndex);
            } else {
                captionOverlay?.classList.add('hidden');
                highlightSegment(-1);
            }
            lastActiveSegmentIndex = activeSegmentIndex;
        }
    }

    // --- Caption Generation ---
    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            const file = videoUpload.files[0];
            if (!file) return;

            processingStatus?.classList.remove('hidden');
            generateBtn.disabled = true;
            aiMessage.innerHTML = "Analyzing audio and generating English captions... 🛰️";

            const formData = new FormData();
            formData.append('video', file);
            formData.append('email', userEmail || '');
            const langSelect = document.getElementById('generate-lang-select');
            formData.append('language', langSelect ? langSelect.value : 'en');

            try {
                const response = await fetch(`${API_BASE_URL}/api/generate-captions`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error(`Server returned ${response.status}`);
                const data = await response.json();

                if (data.status === 'success') {
                    // Use segments if available, fallback to words
                    const segments = data.segments && data.segments.length > 0 ? data.segments : data.words;
                    originalAiCaptions = JSON.parse(JSON.stringify(segments));
                    currentCaptions = segments;
                    lastActiveSegmentIndex = -1; // Reset index
                    renderTranscript();
                    if (aiMessage) {
                        if (data.is_demo) {
                            aiMessage.innerHTML = "<strong>Demo Mode:</strong> Any language is now <strong>English</strong>. Voice, video, and transcript are perfectly synced! 🚀";
                        } else {
                            aiMessage.innerHTML = "<strong>Success!</strong> All languages translated to <strong>English</strong> and synced with transcript! 🎙️✨";
                        }
                    }
                } else if (data.status === 'no_audio' || data.status === 'no_voice') {
                    if (aiMessage) aiMessage.innerHTML = `<span style="color: #e63946;">❌ ${data.message}</span>`;
                    currentCaptions = [];
                    renderWordList();
                } else {
                    throw new Error(data.message || "Unknown error occurred on AI backend");
                }
            } catch (err) {
                console.error("Caption generation failed", err);
                if (aiMessage) aiMessage.innerHTML = `<span style="color: #e63946;">Oops! Error: ${err.message}</span><br><small>Ensure backend is running at http://localhost:8000</small>`;
            } finally {
                processingStatus?.classList.add('hidden');
                generateBtn.disabled = false;
            }
        });
    }

    // --- Export Video Logic ---
    const exportBtn = document.getElementById('export-video-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            const file = videoUpload.files[0];
            if (!file || !currentCaptions.length) {
                alert("Please upload a video and generate captions first.");
                return;
            }

            const activeRes = document.querySelector('.res-btn.active')?.dataset.res || '1080p';
            exportBtn.disabled = true;
            exportBtn.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; justify-content: center;">
                    <div class="spinner" style="width: 16px; height: 16px;"></div>
                    <span>Rendering ${activeRes}...</span>
                </div>
            `;

            const formData = new FormData();
            formData.append('video', file);
            formData.append('segments', JSON.stringify(currentCaptions));

            const styleData = {
                font: fontSelector?.value,
                size: fontSizeSlider?.value,
                color: document.querySelector('.color-swatch.active')?.dataset.color || '#ffffff',
                position: document.querySelector('.pos-btn.active')?.dataset.pos || 'bottom',
                animation: animationSelector?.value
            };
            formData.append('styles', JSON.stringify(styleData));

            try {
                const response = await fetch(`${API_BASE_URL}/api/export-video`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error("Rendering failed on server.");

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `codex7_viral_export_${Date.now()}.mp4`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                showToast(`Successfully exported your viral video!`);
                exportBtn.textContent = "Download Ready ✅";
                setTimeout(() => {
                    exportBtn.textContent = "Export Video";
                    exportBtn.disabled = false;
                }, 2000);

                // Also auto-export transcript text as secondary file
                exportTranscript(true);

            } catch (err) {
                console.error("Export failed", err);
                showToast("Failed to render video. Please try again.", "error");
                exportBtn.textContent = "Export Video";
                exportBtn.disabled = false;
            }
        });
    }

    function exportTranscript(isAuto = false) {
        if (!currentCaptions.length) return;

        const activeColor = document.querySelector('.color-swatch.active')?.dataset.color || '#ffffff';
        const activePos = document.querySelector('.pos-btn.active')?.dataset.pos || 'bottom';
        const activeAnim = animationSelector?.value || 'pop';

        let content = "========================================\n";
        content += "     codex7.ai — AI VIDEO TRANSCRIPT    \n";
        content += "========================================\n\n";
        content += `Timestamp: ${new Date().toLocaleString()}\n`;
        content += `Project: ${videoUpload.files[0]?.name || 'Untitled Project'}\n\n`;

        content += "--- STYLE CONFIGURATION ---\n";
        content += `Font Family: ${fontSelector?.value}\n`;
        content += `Font Size: ${fontSizeSlider?.value}px\n`;
        content += `Highlight Color: ${activeColor}\n`;
        content += `Position: ${activePos}\n`;
        content += `Animation: ${activeAnim}\n\n`;

        content += "--- TRANSCRIPT DATA ---\n";
        currentCaptions.forEach((seg, i) => {
            content += `[Segment ${i + 1}] ${seg.start.toFixed(2)}s - ${seg.end.toFixed(2)}s: "${(seg.text || seg.word || "").toUpperCase()}"\n`;
        });

        content += "\n========================================\n";
        content += "        GENERATED BY CODEX7.AI         \n";
        content += "========================================\n";

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `codex7_export_data_${Date.now()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        if (!isAuto) showToast("Exported transcript with styles! 📄");
    }

    const downloadTranscriptBtn = document.getElementById('download-transcript-btn');
    if (downloadTranscriptBtn) {
        downloadTranscriptBtn.addEventListener('click', () => {
            if (!currentCaptions.length) {
                showToast("No captions to download", "error");
                return;
            }
            exportTranscript(false);
        });
    }

    const resButtons = document.querySelectorAll('.res-btn');
    resButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            resButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // --- Transcript UI (Segment Based) ---
    function renderTranscript() {
        if (!transcriptList) return;
        transcriptList.innerHTML = '';

        if (currentCaptions.length === 0) {
            transcriptList.innerHTML = '<div class="empty-state">No segments detected.</div>';
            return;
        }

        currentCaptions.forEach((seg, index) => {
            const card = document.createElement('div');
            card.className = 'transcript-card';
            card.dataset.index = index;

            card.innerHTML = `
                <span class="card-time">${formatTime(seg.start)} &rarr; ${formatTime(seg.end)}</span>
                <p class="card-text">${seg.text || seg.word}</p>
                <div class="card-save-controls">
                    <textarea class="card-edit-area">${seg.text || seg.word}</textarea>
                    <div style="display: flex; gap: 8px;">
                         <button class="btn-pill save">Save</button>
                         <button class="btn-pill cancel">Cancel</button>
                    </div>
                </div>
                <div class="card-controls">
                    <button class="mini-btn-rounded play" title="Play Segment">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                    </button>
                    <button class="mini-btn-rounded edit" title="Edit Text">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                    </button>
                    <button class="mini-btn-rounded delete" title="Delete Segment">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;

            // Play segment
            card.querySelector('.play').onclick = (e) => {
                e.stopPropagation();
                mainVideo.currentTime = seg.start;
                if (mainVideo.paused) togglePlayback();
            };

            // Edit toggle
            const editBtn = card.querySelector('.edit');
            const saveBtn = card.querySelector('.save');
            const cancelBtn = card.querySelector('.cancel');
            const textarea = card.querySelector('textarea');

            editBtn.onclick = (e) => {
                e.stopPropagation();
                card.classList.add('editing');
                textarea.focus();
            };

            saveBtn.onclick = (e) => {
                e.stopPropagation();
                const newText = textarea.value.trim();
                currentCaptions[index].text = newText;
                card.querySelector('.card-text').textContent = newText;
                card.classList.remove('editing');
                if (index === lastActiveSegmentIndex) syncCaptions();
                showToast("Segment updated!");
            };

            cancelBtn.onclick = (e) => {
                e.stopPropagation();
                textarea.value = seg.text || seg.word;
                card.classList.remove('editing');
            };

            // Card click to seek
            card.addEventListener('click', () => {
                if (card.classList.contains('editing')) return;
                mainVideo.currentTime = seg.start;
                syncCaptions();
            });

            // Delete
            card.querySelector('.delete').onclick = (e) => {
                e.stopPropagation();
                if (confirm("Delete this segment?")) {
                    currentCaptions.splice(index, 1);
                    renderTranscript();
                    showToast("Segment removed");
                }
            };

            transcriptList.appendChild(card);
        });
    }

    function highlightSegment(index) {
        if (!transcriptList) return;
        const cards = transcriptList.querySelectorAll('.transcript-card');
        cards.forEach(c => c.classList.remove('active'));
        if (index !== -1) {
            const activeCard = transcriptList.querySelector(`.transcript-card[data-index="${index}"]`);
            if (activeCard) {
                activeCard.classList.add('active');
                activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    if (snapTimingBtn) {
        snapTimingBtn.addEventListener('click', () => {
            if (originalAiCaptions.length) {
                currentCaptions = JSON.parse(JSON.stringify(originalAiCaptions));
                renderTranscript();
                showToast("Timing snapped back to original AI detection!");
            }
        });
    }

    // --- Save Project Logic ---
    const saveProjectBtn = document.getElementById('save-history-btn');
    if (saveProjectBtn) {
        saveProjectBtn.addEventListener('click', async () => {
            if (!currentCaptions.length) {
                showToast("Nothing to save yet.", "error");
                return;
            }

            saveProjectBtn.disabled = true;
            saveProjectBtn.textContent = "Saving...";

            const formData = new FormData();
            formData.append('email', userEmail);
            formData.append('video_name', videoUpload.files[0]?.name || 'Untitled Video');
            formData.append('caption_text', JSON.stringify(currentCaptions));
            formData.append('font', fontSelector?.value || 'Bebas Neue');
            formData.append('size', fontSizeSlider?.value || '48');
            formData.append('color', document.querySelector('.color-swatch.active')?.dataset.color || '#ffffff');
            formData.append('position', document.querySelector('.pos-btn.active')?.dataset.pos || 'bottom');

            try {
                const res = await fetch(`${API_BASE_URL}/api/save-history`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    showToast("Project saved successfully! ☁️");
                    loadHistory();
                }
            } catch (err) {
                console.error("Save failed", err);
                showToast("Failed to save project", "error");
            } finally {
                saveProjectBtn.disabled = false;
                saveProjectBtn.textContent = "Save Project";
            }
        });
    }

    // --- Customization ---
    // Presets removed as requested

    function applyStyles() {
        if (!captionTextContent) return;
        const font = fontSelector?.value || "'Inter', sans-serif";
        captionTextContent.style.fontFamily = font;
        captionTextContent.style.fontSize = (fontSizeSlider?.value || 32) + 'px';
        if (fontSizeValue) fontSizeValue.textContent = (fontSizeSlider?.value || 32) + 'px';

        const activeColor = document.querySelector('.color-swatch.active')?.dataset.color || colorPicker?.value || '#ffffff';
        captionTextContent.style.color = activeColor;

        const activePosBtn = document.querySelector('.pos-btn.active');
        if (activePosBtn && captionOverlay) {
            captionOverlay.className = 'caption-overlay ' + activePosBtn.dataset.pos;
        }

        // Apply viral-specific rules if Bebas Neue is selected
        if (font.includes('Bebas')) {
            captionTextContent.style.textTransform = 'uppercase';
        } else {
            captionTextContent.style.textTransform = 'none';
        }

        // Toggles
        const bgBox = document.getElementById('bg-box-toggle');
        const shadow = document.getElementById('shadow-toggle');

        if (bgBox && bgBox.checked) {
            captionTextContent.classList.add('caption-bg-box');
        } else {
            captionTextContent.classList.remove('caption-bg-box');
        }

        if (shadow && shadow.checked) {
            captionTextContent.classList.add('caption-shadow');
        } else {
            captionTextContent.classList.remove('caption-shadow');
        }
    }

    // Toggle Listeners
    document.getElementById('bg-box-toggle')?.addEventListener('change', applyStyles);
    document.getElementById('shadow-toggle')?.addEventListener('change', applyStyles);

    fontSelector?.addEventListener('change', applyStyles);
    fontSizeSlider?.addEventListener('input', applyStyles);

    colorPicker?.addEventListener('input', () => {
        colorSwatches.forEach(s => s.classList.remove('active'));
        applyStyles();
    });

    colorSwatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
            colorSwatches.forEach(s => s.classList.remove('active'));
            swatch.classList.add('active');
            applyStyles();
        });
    });

    posButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            posButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyStyles();
        });
    });

    // --- Particle Background Logic ---
    function initParticles() {
        const container = document.getElementById('particles-bg');
        if (!container) return;

        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        const ctx = canvas.getContext('2d');

        let particles = [];
        let mouse = { x: null, y: null, radius: 150 };

        window.addEventListener('mousemove', (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.baseX = this.x;
                this.baseY = this.y;
                this.density = (Math.random() * 40) + 5;
                this.velocity = {
                    x: (Math.random() - 0.5) * 1,
                    y: (Math.random() - 0.5) * 1
                };
            }

            draw() {
                ctx.fillStyle = 'rgba(255, 77, 79, 0.4)'; /* Matches new primary red */
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.closePath();
                ctx.fill();
            }

            update() {
                this.x += this.velocity.x;
                this.y += this.velocity.y;

                if (this.x > canvas.width || this.x < 0) this.velocity.x *= -1;
                if (this.y > canvas.height || this.y < 0) this.velocity.y *= -1;

                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < mouse.radius) {
                    const forceDirectionX = dx / distance;
                    const forceDirectionY = dy / distance;
                    const force = (mouse.radius - distance) / mouse.radius;
                    const directionX = forceDirectionX * force * this.density;
                    const directionY = forceDirectionY * force * this.density;

                    this.x -= directionX * 0.1;
                    this.y -= directionY * 0.1;
                }
            }
        }

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            init();
        }

        function init() {
            particles = [];
            let numberOfParticles = (canvas.width * canvas.height) / 10000;
            for (let i = 0; i < numberOfParticles; i++) {
                particles.push(new Particle());
            }
        }

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.draw();
                p.update();
            });
            requestAnimationFrame(animate);
        }

        window.addEventListener('resize', resize);
        resize();
        animate();
    }

    // --- UX Feedback System ---
    const feedbackModal = document.getElementById('feedback-modal');
    const openFeedbackBtn = document.getElementById('open-feedback-btn');
    const closeFeedbackBtn = document.getElementById('close-feedback');
    const feedbackForm = document.getElementById('feedback-form');
    const starSpan = document.querySelectorAll('.star-rating span');
    const ratingInput = document.getElementById('rating-value');

    if (openFeedbackBtn) {
        openFeedbackBtn.addEventListener('click', () => feedbackModal.classList.remove('hidden'));
    }

    if (closeFeedbackBtn) {
        closeFeedbackBtn.addEventListener('click', () => feedbackModal.classList.add('hidden'));
    }

    // Star Rating Interaction
    starSpan.forEach(star => {
        star.addEventListener('click', () => {
            const val = parseInt(star.dataset.star);
            ratingInput.value = val;

            // Visual Update
            starSpan.forEach(s => {
                s.textContent = parseInt(s.dataset.star) <= val ? '★' : '☆';
            });
        });
    });

    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const feedbackData = {
                user_id: userEmail || 'anonymous',
                rating: parseInt(ratingInput.value),
                message: document.getElementById('feedback-msg').value,
                feature: document.getElementById('fb-feature').value || 'Editor',
                language_pref: document.getElementById('fb-lang').value
            };

            if (feedbackData.rating === 0) {
                showToast("Please select a star rating", "error");
                return;
            }

            try {
                const res = await fetch(`${API_BASE_URL}/api/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(feedbackData)
                });

                if (res.ok) {
                    showToast("Feedback submitted! You're awesome. ✨");
                    feedbackModal.classList.add('hidden');
                    feedbackForm.reset();
                    starSpan.forEach(s => s.textContent = '☆');
                }
            } catch (err) {
                console.error("Feedback failed", err);
                showToast("Failed to send feedback", "error");
            }
        });
    }

    // --- Logout & Logo ---
    // Exit button logic removed as requested

    document.querySelector('.brand-logo')?.addEventListener('click', () => {
        window.location.href = 'index.html';
    });
});

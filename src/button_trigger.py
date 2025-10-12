async function addNewCalendarV1() {
    const modalContent = document.getElementById('modal-content');
    if (!modalContent) {
        console.warn('[addNewCalendarV1] #modal-content not found.');
        return;
    }

    const user = getCurrentUser?.();
    if (!user?.buwana_id) {
        alert('Please log in to create a calendar.');
        if (typeof sendUpRegistration === 'function') sendUpRegistration();
        return;
    }

    // Ensure modal positioning
    const computedPosition = window.getComputedStyle(modalContent).position;
    if (computedPosition === 'static' && !modalContent.dataset.originalPosition) {
        modalContent.dataset.originalPosition = 'static';
        modalContent.style.position = 'relative';
    }

    // Remove any existing overlay
    const existingOverlay = document.getElementById('ec-add-calendar-overlay');
    if (existingOverlay) {
        if (typeof existingOverlay.__ecTeardown === 'function') {
            existingOverlay.__ecTeardown();
        } else {
            existingOverlay.remove();
        }
    }

    // Build overlay
    const overlay = document.createElement('div');
    overlay.id = 'ec-add-calendar-overlay';
    overlay.classList.add('main-background');
    Object.assign(overlay.style, {
        position: 'absolute',
        inset: '0',
        zIndex: '20',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        gap: '20px',
        overflowY: 'auto',
        borderRadius: '10px',
        background: 'var(--general-background)'
    });

    overlay.innerHTML = `
        <div class="ec-add-calendar-header" style="display:flex;flex-direction:column;gap:8px;">
            <h2 style="margin:0;font-size:1.5rem;">Add New Calendar</h2>
            <p style="margin:0;color:var(--subdued-text);font-size:0.95rem;">
                Private calendars help you manage personal events, public calendars let folks subscribe to your lists of events.
            </p>
        </div>
        <form id="ec-add-calendar-form" style="display:flex;flex-direction:column;gap:16px;">
            <label style="display:flex;flex-direction:column;gap:6px;font-weight:600;">
                <span style="font-size:0.95rem;">Calendar name</span>
                <input id="ec-cal-name" name="calendar_name" type="text" placeholder="Name your new calendar..." required
                       style="padding:10px;border-radius:8px;border:1px solid var(--subdued-text, #d1d5db);font-weight:400;" />
            </label>
            <label style="display:flex;flex-direction:column;gap:6px;font-weight:600;">
                <span style="font-size:0.95rem;">Description</span>
                <textarea id="ec-cal-description" name="calendar_description" rows="3"
                          placeholder="Describe what this calendar is for"
                          style="padding:10px;border-radius:8px;border:1px solid grey;font-weight:400;resize:vertical;background:var(--top-header)"></textarea>
            </label>
            <div style="display:flex;gap:12px;align-items:flex-end;">
                <label style="flex:1;display:flex;flex-direction:column;gap:6px;font-weight:600;">
                    <span style="font-size:0.95rem;">Calendar category</span>
                    <select id="ec-cal-category" name="calendar_category"
                            style="padding:10px;border-radius:8px;border:1px solid var(--subdued-text, #d1d5db);font-weight:400;">
                        <option value="" disabled selected>Select calendar category...</option>
                        <option value="personal">Personal</option>
                        <option value="holidays">Holidays</option>
                        <option value="birthdays">Birthdays</option>
                        <option value="astronomy">Astronomy</option>
                        <option value="migration">Migration</option>
                        <option value="other">Other</option>
                    </select>
                </label>
                <div class="ec-inline-field ec-emoji-field" style="width:auto;">
                    <div class="ec-emoji-input">
                        <button type="button" id="ec-cal-emoji-button" class="blur-form-field ec-emoji-button"
                                aria-haspopup="true" aria-expanded="false" aria-label="Choose calendar emoji"
                                style="width:45px;height:45px;display:flex;align-items:center;justify-content:center;">
                            <span id="ec-cal-emoji-preview" class="ec-emoji-preview">🌍</span>
                        </button>
                        ${buildEmojiPicker('ec-cal-emoji-picker')}
                        <input type="hidden" id="ec-cal-emoji" name="calendar_emoji" value="🌍">
                    </div>
                </div>
            </div>
            <div style="display:flex;gap:12px;align-items:flex-end;">
                <label style="flex:1;display:flex;flex-direction:column;gap:6px;font-weight:600;">
                    <span style="font-size:0.95rem;">Visibility</span>
                    <select id="ec-cal-visibility" name="calendar_visibility"
                            style="padding:10px;border-radius:8px;border:1px solid var(--subdued-text, #d1d5db);font-weight:400;">
                        <option value="public">Public</option>
                        <option value="private" selected>Private</option>
                    </select>
                </label>
                <div class="ec-inline-field ec-color-field" style="width:auto;">
                    <input id="ec-cal-color" name="calendar_color" type="color" value="#ff6b6b"
                           class="blur-form-field ec-color-input" aria-label="Calendar color"
                           style="width:45px;height:45px;padding:0;">
                </div>
            </div>
            <div class="ec-add-calendar-actions" style="margin-top:8px;">
                <button type="submit" style="width:100%;padding:12px 20px;border-radius:999px;border:none;
                        background:var(--h1, #2563eb);color:#fff;font-weight:600;cursor:pointer;">Create calendar</button>
            </div>
        </form>
    `;

    // 🧩 Append overlay to modal
    modalContent.appendChild(overlay);

    // 🧠 Emoji picker integration
    const detachEmojiPicker = wireEmojiPicker({
        buttonId: 'ec-cal-emoji-button',
        pickerId: 'ec-cal-emoji-picker',
        hiddenInputId: 'ec-cal-emoji',
        previewId: 'ec-cal-emoji-preview',
        defaultEmoji: '🌍'
    });

    // 🔁 Restore modal position on close
    const restoreModalPosition = () => {
        if (modalContent.dataset.originalPosition === 'static') {
            modalContent.style.position = '';
            delete modalContent.dataset.originalPosition;
        }
    };

    // 🔒 Close overlay handler
    const closeButton = document.querySelector('#form-modal-message .x-button');
    const originalCloseHandler = closeButton ? closeButton.onclick : null;
    const originalCloseAttr = closeButton ? closeButton.getAttribute('onclick') : null;

    const teardownOverlay = () => {
        detachEmojiPicker();
        if (overlay.parentElement) overlay.remove();
        restoreModalPosition();
        if (closeButton) {
            closeButton.onclick = originalCloseHandler || null;
            if (originalCloseAttr !== null) {
                closeButton.setAttribute('onclick', originalCloseAttr);
            } else {
                closeButton.removeAttribute('onclick');
            }
        }
        delete overlay.__ecTeardown;
    };
    overlay.__ecTeardown = teardownOverlay;

    if (closeButton) {
        closeButton.onclick = (event) => {
            event.preventDefault();
            event.stopImmediatePropagation?.();
            teardownOverlay();
        };
    }

    // 📨 Form submission
    const form = overlay.querySelector('#ec-add-calendar-form');
    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const payload = {
                buwana_id: user.buwana_id,
                name: valueOf('#ec-cal-name'),
                description: valueOf('#ec-cal-description'),
                emoji: valueOf('#ec-cal-emoji'),
                color: valueOf('#ec-cal-color'),
                category: valueOf('#ec-cal-category'),
                visibility: valueOf('#ec-cal-visibility'),
                tzid: getUserTZ()
            };

            console.log('[addNewCalendarV1] Submitting new calendar:', payload);

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating…';

            try {
                const res = await fetch('/api/v1/add_new_cal.php', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify(payload)
                });

                const data = await res.json().catch(() => ({}));
                console.log('[addNewCalendarV1] Response:', data);

                if (!res.ok || !data.ok) {
                    alert(data?.error || 'Could not create your calendar. Please try again.');
                    return;
                }

                // ✅ Success — Close overlay & refresh calendars
                alert(`✅ Calendar "${payload.name}" created successfully!`);
                teardownOverlay();

                if (typeof loadUserCalendars === 'function') {
                    await loadUserCalendars(user.buwana_id, { force: true });
                }

            } catch (err) {
                console.error('[addNewCalendarV1] Error creating calendar:', err);
                alert('Network error — could not reach the server.');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
}

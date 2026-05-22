document.addEventListener('DOMContentLoaded', async () => {
    let allEvents = [];
    let filteredEvents = [];
    
    // DOM Elements
    const grid = document.getElementById('event-grid');
    const loadingState = document.getElementById('loading-state');
    const emptyState = document.getElementById('empty-state');
    const searchInput = document.getElementById('search-input');
    const typeBtns = document.querySelectorAll('.type-filters .filter-btn');
    const wardFilter = document.getElementById('ward-filter');
    const priceFilter = document.getElementById('price-filter');
    const ageFilter = document.getElementById('age-filter');
    const resetBtn = document.getElementById('reset-filters');
    const scoreFilter = document.getElementById('score-filter');
    const scoreVal = document.getElementById('score-val');
    
    const dateStartFilter = document.getElementById('date-start-filter');
    const dateEndFilter = document.getElementById('date-end-filter');
    const navItems = document.querySelectorAll('.nav-item');
    const viewPanels = document.querySelectorAll('.view-panel');
    
    // State
    const state = {
        type: 'all',
        search: '',
        ward: 'all',
        price: 'all',
        age: 'all',
        score: 30,
        dateStart: '',
        dateEnd: '',
        activeView: 'list' // list, calendar, type, age
    };

    window.formatEventDate = function(dateStartStr, dateEndStr, eventPeriod) {
        if (eventPeriod && !(/^\d{4}-\d{2}-\d{2}$/.test(eventPeriod))) {
            return eventPeriod;
        }
        const start = dateStartStr || eventPeriod || '';
        const end = dateEndStr || '';
        if (!start) return '未知时间';
        
        const toMD = (str) => {
            const parts = str.split('-');
            if (parts.length >= 3) {
                return `${parseInt(parts[1], 10)}月${parseInt(parts[2], 10)}日`;
            }
            return str;
        };
        
        if (start === end || !end) {
            return toMD(start);
        } else {
            return `${toMD(start)} - ${toMD(end)}`;
        }
    }
    
    // Configuration mapping
    const typeMap = {
        'outdoor': '自然户外',
        'arts': '手工艺术',
        'science': '科学体验',
        'sports': '运动竞技',
        'culture': '文化节庆',
        'nature': '自然农场',
        'museum': '博物展览',
        'performance': '演出舞台'
    };

    // Initialize
    async function init() {
        // Set default date range: today to +30 days
        const today = new Date();
        const future = new Date(today);
        future.setDate(today.getDate() + 30);
        
        const formatDate = (d) => d.toISOString().split('T')[0];
        state.dateStart = formatDate(today);
        state.dateEnd = formatDate(future);
        dateStartFilter.value = state.dateStart;
        dateEndFilter.value = state.dateEnd;
        
        try {
            const response = await fetch('data/index.json');
            if (!response.ok) throw new Error('Data not found');
            allEvents = await response.json();
            
            // Populate wards dynamically based on data
            populateWards();
            
            // Initial render
            applyFilters();
            
        } catch (error) {
            console.error('Error loading events:', error);
            loadingState.style.display = 'none';
            emptyState.style.display = 'block';
            emptyState.querySelector('p').textContent = '数据加载失败，请确保您通过 HTTP 服务器访问或数据文件存在。';
            
            // For local testing without server, populate dummy data if data fetch fails
            if (window.location.protocol === 'file:') {
                console.log('Loading dummy data for local file:// testing');
                loadDummyData();
            }
        }
        
        setupEventListeners();
    }
    
    function loadDummyData() {
        allEvents = [
            { id: '1', date: '2026-05-20', title_zh: '代代木公园春季儿童自然考察', type: 'outdoor', ward: '渋谷区', age_min: 3, age_max: 8, free: true, summary_zh: '由植物专家带领的自然考察活动，孩子们可以认识各种春季植物和昆虫。\n\n**注意事项**：请穿着舒适的运动鞋。' },
            { id: '2', date: '2026-05-21', title_zh: '新宿区立科学馆：奇妙的物理世界', type: 'science', ward: '新宿区', age_min: 6, age_max: 12, free: false, price: 500, indoor: true, summary_zh: '通过互动的物理实验，了解重力、磁力的奇妙原理。' },
            { id: '3', date: '2026-05-22', title_zh: '港区亲子陶艺体验', type: 'arts', ward: '港区', age_min: 4, age_max: 10, free: false, price: 1500, indoor: true, summary_zh: '亲子共同制作属于自己的陶瓷水杯，锻炼孩子的动手能力。' },
        ];
        populateWards();
        applyFilters();
    }
    
    function populateWards() {
        const wards = new Set();
        allEvents.forEach(e => {
            if (e.ward) wards.add(e.ward);
        });
        
        const sortedWards = Array.from(wards).sort();
        wardFilter.innerHTML = '<option value="all">所有区域 (Wards)</option>';
        sortedWards.forEach(ward => {
            const option = document.createElement('option');
            option.value = ward;
            option.textContent = ward;
            wardFilter.appendChild(option);
        });
    }
    
    function setupEventListeners() {
        // Search
        searchInput.addEventListener('input', (e) => {
            state.search = e.target.value.trim().toLowerCase();
            applyFilters();
        });
        
        // Type Buttons
        typeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                typeBtns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                state.type = e.target.dataset.type;
                applyFilters();
            });
        });
        
        // Select Filters
        wardFilter.addEventListener('change', (e) => { state.ward = e.target.value; applyFilters(); });
        priceFilter.addEventListener('change', (e) => { state.price = e.target.value; applyFilters(); });
        ageFilter.addEventListener('change', (e) => { state.age = e.target.value; applyFilters(); });
        
        // Score Slider
        if (scoreFilter) {
            scoreFilter.addEventListener('input', (e) => {
                state.score = parseInt(e.target.value, 10);
                if (scoreVal) scoreVal.textContent = state.score;
                applyFilters();
            });
        }
        
        // Date Filters
        dateStartFilter.addEventListener('change', (e) => { state.dateStart = e.target.value; applyFilters(); });
        dateEndFilter.addEventListener('change', (e) => { state.dateEnd = e.target.value; applyFilters(); });
        
        // Navigation Views
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                navItems.forEach(n => n.classList.remove('active'));
                
                let target = e.target;
                while (!target.classList.contains('nav-item')) {
                    target = target.parentElement;
                }
                target.classList.add('active');
                
                state.activeView = target.dataset.view;
                
                viewPanels.forEach(p => p.style.display = 'none');
                document.getElementById(`${state.activeView}-view`).style.display = 'block';
                
                renderEvents(); // Re-render for the active view
            });
        });
        
        // Reset
        resetBtn.addEventListener('click', () => {
            state.type = 'all';
            state.search = '';
            state.ward = 'all';
            state.price = 'all';
            state.age = 'all';
            
            searchInput.value = '';
            wardFilter.value = 'all';
            priceFilter.value = 'all';
            ageFilter.value = 'all';
            if (scoreFilter) scoreFilter.value = 30;
            if (scoreVal) scoreVal.textContent = 30;
            state.score = 30;
            
            const today = new Date();
            const future = new Date(today);
            future.setDate(today.getDate() + 30);
            state.dateStart = today.toISOString().split('T')[0];
            state.dateEnd = future.toISOString().split('T')[0];
            dateStartFilter.value = state.dateStart;
            dateEndFilter.value = state.dateEnd;
            
            typeBtns.forEach(b => b.classList.remove('active'));
            document.querySelector('.filter-btn[data-type="all"]').classList.add('active');
            
            applyFilters();
        });
        
        // Modal Close
        const modalCloseBtn = document.getElementById('modal-close-btn');
        const modal = document.getElementById('event-modal');
        if (modalCloseBtn && modal) {
            modalCloseBtn.addEventListener('click', () => { modal.style.display = 'none'; });
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.style.display = 'none';
            });
        }
    }
    
    function applyFilters() {
        filteredEvents = allEvents.filter(event => {
            // Type match
            if (state.type !== 'all' && event.type !== state.type) return false;
            
            // Ward match
            if (state.ward !== 'all' && event.ward !== state.ward) return false;
            
            // Price match
            if (state.price === 'free' && event.free !== true) return false;
            if (state.price === 'paid' && event.free === true) return false;
            if (state.price !== 'all' && state.price !== 'free' && state.price !== 'paid') {
                const price = event.price !== undefined && event.price !== null ? event.price : (event.free ? 0 : null);
                if (price === null) return false; // 如果价格未知且非免费，不展示
                if (state.price === '1-1000') {
                    if (price < 1 || price > 1000) return false;
                } else if (state.price === '1000-3000') {
                    if (price < 1000 || price > 3000) return false;
                } else if (state.price === '3000+') {
                    if (price < 3000) return false;
                }
            }
            
            // Score match
            const eventScore = event.ai_score !== undefined && event.ai_score !== null ? event.ai_score : 0;
            if (eventScore < state.score) return false;
            
            // Age match (simple overlap logic)
            if (state.age !== 'all') {
                const [min, max] = state.age.split('-').map(Number);
                const eventMin = event.age_min !== undefined ? event.age_min : 0;
                const eventMax = event.age_max !== undefined ? event.age_max : 18;
                // Check if ranges overlap
                if (eventMax < min || eventMin > max) return false;
            }
            
            // Date match
            if (state.dateStart && event.date && event.date < state.dateStart) return false;
            if (state.dateEnd && event.date && event.date > state.dateEnd) return false;
            
            // Search match
            if (state.search) {
                const searchStr = `${event.title_zh || ''} ${event.title_ja || ''} ${event.venue || ''} ${event.ward || ''}`.toLowerCase();
                if (!searchStr.includes(state.search)) return false;
            }
            
            return true;
        });
        
        renderEvents();
    }
    
    function renderEvents() {
        if (state.activeView === 'list') {
            renderListView();
        } else if (state.activeView === 'calendar') {
            window.CalendarView.render(filteredEvents, 'calendar-container');
            emptyState.style.display = 'none';
        } else if (state.activeView === 'type') {
            window.GroupView.renderByType(filteredEvents, 'type-container');
            emptyState.style.display = 'none';
        } else if (state.activeView === 'age') {
            window.GroupView.renderByAge(filteredEvents, 'age-container');
            emptyState.style.display = 'none';
        }
    }
    
    function renderListView() {
        loadingState.style.display = 'none';
        
        if (filteredEvents.length === 0) {
            grid.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        grid.innerHTML = '';
        
        // Ensure marked.js is available
        const md = window.marked ? window.marked.parse : (text) => `<p>${text}</p>`;
        
        filteredEvents.forEach(event => {
            const card = document.createElement('div');
            card.className = `event-card type-${event.type || 'default'}`;
            
            // Format Tags
            let tagsHtml = '';
            if (event.age_min !== undefined && event.age_max !== undefined) {
                tagsHtml += `<span class="tag tag-age">${event.age_min}-${event.age_max}岁</span>`;
            }
            if (event.free) {
                tagsHtml += `<span class="tag tag-free">免费</span>`;
            }
            if (event.type && typeMap[event.type]) {
                tagsHtml += `<span class="tag tag-type">${typeMap[event.type]}</span>`;
            }
            if (event.indoor) {
                tagsHtml += `<span class="tag tag-indoor">室内</span>`;
            }
            if (event.ai_score !== undefined && event.ai_score !== null) {
                tagsHtml += `<span class="tag tag-score"><i class="fa-solid fa-star"></i> ${parseFloat(event.ai_score).toFixed(1)}</span>`;
            }

            // Date formatting
            const dateStr = formatEventDate(event.date_start, event.date_end, event.event_period || event.date);

            // Image formatting
            let imgHtml = '';
            if (event.image_url) {
                imgHtml = `
                    <div class="card-image-wrapper">
                        <img src="${event.image_url}" alt="${event.title_zh || '活动图片'}" class="card-image" loading="lazy" onerror="this.parentElement.style.display='none';">
                    </div>
                `;
            }

            card.innerHTML = `
                ${imgHtml}
                <div class="card-body">
                    <div class="card-header">
                        <div class="card-tags">${tagsHtml}</div>
                        <div class="card-date">${dateStr}</div>
                    </div>
                    <h3 class="card-title">${event.title_zh || event.title_ja || '未知活动'}</h3>
                    <div class="card-meta">
                        ${event.ward || event.venue ? `<span><i class="fa-solid fa-location-dot"></i> ${event.ward || ''} ${event.venue || ''}</span>` : ''}
                        ${event.time_start ? `<span><i class="fa-regular fa-clock"></i> ${event.time_start}${event.time_end ? ' - ' + event.time_end : ''}</span>` : ''}
                    </div>
                </div>
            `;
            
            // Add click event for full detail modal
            card.addEventListener('click', () => {
                window.showEventModal(event);
            });
            
            grid.appendChild(card);
        });
    }
    
    // Global Event Detail Modal renderer (shared with all views)
    window.showEventModal = async function(event) {
        const modal = document.getElementById('event-modal');
        const modalBody = document.getElementById('modal-body');
        if (!modal || !modalBody) return;
        
        modal.style.display = 'flex';
        modalBody.innerHTML = '<div class="spinner"></div><p class="modal-loading-text">加载详情中...</p>';
        
        // Tags HTML
        let tagsHtml = '';
        if (event.age_min !== undefined && event.age_max !== undefined) {
            tagsHtml += `<span class="tag tag-age">${event.age_min}-${event.age_max}岁</span>`;
        }
        if (event.free) {
            tagsHtml += `<span class="tag tag-free">免费</span>`;
        }
        if (event.type && typeMap[event.type]) {
            tagsHtml += `<span class="tag tag-type">${typeMap[event.type]}</span>`;
        }
        if (event.indoor) {
            tagsHtml += `<span class="tag tag-indoor">室内</span>`;
        }
        if (event.ai_score !== undefined && event.ai_score !== null) {
            tagsHtml += `<span class="tag tag-score"><i class="fa-solid fa-star"></i> ${parseFloat(event.ai_score).toFixed(1)}</span>`;
        }
        
        const md = window.marked ? window.marked.parse : (text) => `<p>${text}</p>`;
        
        try {
            const res = await fetch(`data/events/${event.date}.json`);
            if (!res.ok) throw new Error('Details not available');
            const dayEvents = await res.json();
            const detail = dayEvents.find(e => e.id === event.id) || event;
            
            // 使用 event_period 或是 fallback
            const finalPeriod = formatEventDate(detail.date_start, detail.date_end, detail.event_period || detail.date);
            
            modalBody.innerHTML = `
                ${detail.image_url ? `
                <div class="modal-image-container">
                    <img src="${detail.image_url}" alt="${detail.title_zh || '活动图片'}" class="modal-image" onerror="this.parentElement.style.display='none';">
                </div>
                ` : ''}
                <div class="card-tags modal-tags">${tagsHtml}</div>
                <h2 class="modal-title">${detail.title_zh || detail.title_ja}</h2>
                ${detail.title_ja && detail.title_zh !== detail.title_ja ? `<p class="modal-subtitle">${detail.title_ja}</p>` : ''}
                
                <div class="card-meta modal-meta-container">
                    <span><i class="fa-regular fa-clock"></i> ${finalPeriod} ${detail.time_start || ''} ${detail.time_end ? '- '+detail.time_end : ''}</span>
                    <span><i class="fa-solid fa-location-dot"></i> ${detail.ward || ''} ${detail.venue || ''}</span>
                    ${detail.address ? `<span><i class="fa-solid fa-map-pin"></i> ${detail.address}</span>` : ''}
                    ${detail.price !== undefined ? `<span><i class="fa-solid fa-yen-sign"></i> ${detail.price === 0 ? '免费' : detail.price + ' 日元'}</span>` : ''}
                </div>
                
                <div class="card-summary modal-summary">
                    ${detail.summary_zh ? md(detail.summary_zh) : md(event.summary_zh || '暂无详细介绍')}
                </div>
                
                ${detail.source_url ? `<div class="modal-action-btn-wrapper"><a href="${detail.source_url}" target="_blank" class="modal-action-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> 查看官方活动详情</a></div>` : ''}
            `;
        } catch (err) {
            console.error(err);
            const finalPeriod = formatEventDate(event.date_start, event.date_end, event.event_period || event.date);
            modalBody.innerHTML = `
                ${event.image_url ? `
                <div class="modal-image-container">
                    <img src="${event.image_url}" alt="${event.title_zh || '活动图片'}" class="modal-image" onerror="this.parentElement.style.display='none';">
                </div>
                ` : ''}
                <div class="card-tags modal-tags">${tagsHtml}</div>
                <h2 class="modal-title-fallback">${event.title_zh || event.title_ja}</h2>
                <div class="card-meta modal-meta-container">
                    <span><i class="fa-regular fa-clock"></i> ${finalPeriod} ${event.time_start || ''} ${event.time_end ? '- '+event.time_end : ''}</span>
                    <span><i class="fa-solid fa-location-dot"></i> ${event.ward || ''} ${event.venue || ''}</span>
                </div>
                <div class="card-summary modal-summary">${event.summary_zh ? md(event.summary_zh) : '<p>暂无详细介绍</p>'}</div>
                ${event.source_url ? `<div class="modal-action-btn-wrapper"><a href="${event.source_url}" target="_blank" class="modal-action-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> 查看官方活动详情</a></div>` : ''}
            `;
        }
    };
    
    // ── 意见反馈逻辑 ───────────────────────────────────────
    const feedbackTriggerBtn = document.getElementById('feedback-trigger-btn');
    const feedbackModal = document.getElementById('feedback-modal');
    const feedbackCloseBtn = document.getElementById('feedback-close-btn');
    const feedbackForm = document.getElementById('feedback-form');
    const feedbackSubmitBtn = document.getElementById('feedback-submit-btn');
    const feedbackStatusMsg = document.getElementById('feedback-status-msg');

    // 打开反馈弹窗
    if (feedbackTriggerBtn && feedbackModal) {
        feedbackTriggerBtn.addEventListener('click', () => {
            feedbackModal.style.display = 'flex';
            if (feedbackStatusMsg) feedbackStatusMsg.style.display = 'none';
            feedbackForm.reset();
        });
    }

    // 关闭反馈弹窗
    if (feedbackCloseBtn && feedbackModal) {
        feedbackCloseBtn.addEventListener('click', () => {
            feedbackModal.style.display = 'none';
        });
    }

    // 点击弹窗外部关闭
    window.addEventListener('click', (e) => {
        if (feedbackModal && e.target === feedbackModal) {
            feedbackModal.style.display = 'none';
        }
    });

    init();
});

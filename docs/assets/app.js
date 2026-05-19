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
        dateStart: '',
        dateEnd: '',
        activeView: 'list' // list, calendar, type, age
    };
    
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
                tagsHtml += `<span class="tag tag-type" style="background:#E3F2FD; color:#1565C0;">室内</span>`;
            }
            
            // Date formatting
            const dateStr = event.date || '未定';
            
            const summaryHtml = event.summary_zh ? md(event.summary_zh) : '<p>暂无详细介绍</p>';
            
            card.innerHTML = `
                <div class="card-header">
                    <div class="card-tags">${tagsHtml}</div>
                    <div class="card-date">${dateStr}</div>
                </div>
                <h3 class="card-title">${event.title_zh || event.title_ja || '未知活动'}</h3>
                <div class="card-meta">
                    ${event.ward || event.venue ? `<span><i class="fa-solid fa-location-dot"></i> ${event.ward || ''} ${event.venue || ''}</span>` : ''}
                    ${event.time_start ? `<span><i class="fa-regular fa-clock"></i> ${event.time_start}${event.time_end ? ' - ' + event.time_end : ''}</span>` : ''}
                </div>
                <div class="card-summary">
                    ${summaryHtml}
                </div>
            `;
            
            // Add click event for full detail modal
            card.addEventListener('click', async () => {
                const modal = document.getElementById('event-modal');
                const modalBody = document.getElementById('modal-body');
                if (!modal || !modalBody) return;
                
                modal.style.display = 'flex';
                modalBody.innerHTML = '<div class="spinner"></div><p style="text-align:center;">加载详情中...</p>';
                
                try {
                    // Try to load detailed JSON for this day
                    const res = await fetch(`data/events/${event.date}.json`);
                    if (!res.ok) throw new Error('Details not available');
                    const dayEvents = await res.json();
                    const detail = dayEvents.find(e => e.id === event.id) || event;
                    
                    modalBody.innerHTML = `
                        <div class="card-tags" style="margin-bottom:12px;">${tagsHtml}</div>
                        <h2 style="margin-bottom: 8px; color: var(--text-dark);">${detail.title_zh || detail.title_ja}</h2>
                        ${detail.title_ja && detail.title_zh !== detail.title_ja ? `<p style="color:var(--text-muted); margin-bottom:16px; font-size:14px;">${detail.title_ja}</p>` : ''}
                        
                        <div class="card-meta" style="margin-bottom: 24px; padding: 16px; background: #F8F9FA; border-radius: 12px;">
                            <span><i class="fa-regular fa-clock"></i> ${detail.date} ${detail.time_start || ''} ${detail.time_end ? '- '+detail.time_end : ''}</span>
                            <span><i class="fa-solid fa-location-dot"></i> ${detail.ward || ''} ${detail.venue || ''}</span>
                            ${detail.address ? `<span><i class="fa-solid fa-map-pin"></i> ${detail.address}</span>` : ''}
                            ${detail.price !== undefined ? `<span><i class="fa-solid fa-yen-sign"></i> ${detail.price === 0 ? '免费' : detail.price + ' 日元'}</span>` : ''}
                        </div>
                        
                        <div class="card-summary" style="font-size: 15px; line-height: 1.8; color: #333;">
                            ${detail.summary_zh ? md(detail.summary_zh) : md(event.summary_zh || '暂无详细介绍')}
                        </div>
                        
                        ${detail.source_url ? `<div style="margin-top: 32px; text-align: center;"><a href="${detail.source_url}" target="_blank" style="display:inline-block; padding:12px 32px; background:var(--color-science); color:white; text-decoration:none; border-radius:100px; font-weight:600; box-shadow:0 4px 12px rgba(33, 150, 243, 0.3); transition: transform 0.2s;"><i class="fa-solid fa-arrow-up-right-from-square"></i> 查看官方活动详情</a></div>` : ''}
                    `;
                } catch (err) {
                    console.error(err);
                    // Fallback to basic info if detail file missing
                    modalBody.innerHTML = `
                        <div class="card-tags" style="margin-bottom:12px;">${tagsHtml}</div>
                        <h2 style="margin-bottom: 16px;">${event.title_zh || event.title_ja}</h2>
                        <div class="card-summary" style="font-size: 15px; line-height: 1.8; color: #333;">${summaryHtml}</div>
                    `;
                }
            });
            
            grid.appendChild(card);
        });
    }
    
    init();
});

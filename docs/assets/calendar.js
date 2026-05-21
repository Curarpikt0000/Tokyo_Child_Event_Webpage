// calendar.js
// 包含高保真月历网格组件及侧边栏类型、年龄交互列表（强化起止时间连线及常驻彩色标签）

window.CalendarView = {
    currentYear: null,
    currentMonth: null,
    events: [],
    containerId: null,
    
    render: function(events, containerId) {
        this.events = events;
        this.containerId = containerId;
        
        // 如果年月未初始化，基于当前选择的最早/最新日期或当天日期进行初始化
        if (this.currentYear === null || this.currentMonth === null) {
            let initialDate = new Date();
            const validDates = events.map(e => e.date).filter(Boolean).sort();
            if (validDates.length > 0) {
                initialDate = new Date(validDates[0]);
            }
            this.currentYear = initialDate.getFullYear();
            this.currentMonth = initialDate.getMonth(); // 0-11
        }
        
        this.draw();
    },
    
    draw: function() {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        // 创建外壳
        const calendarContainer = document.createElement('div');
        calendarContainer.className = 'month-calendar-container';
        
        // 头部导航
        const header = document.createElement('div');
        header.className = 'month-calendar-header';
        
        const title = document.createElement('div');
        title.className = 'month-calendar-title';
        title.innerHTML = `<i class="fa-regular fa-calendar-days" style="color:var(--color-science);"></i> ${this.currentYear} 年 ${this.currentMonth + 1} 月`;
        
        const nav = document.createElement('div');
        nav.className = 'month-calendar-nav';
        
        const prevBtn = document.createElement('button');
        prevBtn.className = 'month-calendar-nav-btn';
        prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
        prevBtn.title = "上个月";
        prevBtn.addEventListener('click', () => {
            this.currentMonth--;
            if (this.currentMonth < 0) {
                this.currentMonth = 11;
                this.currentYear--;
            }
            this.draw();
        });
        
        const nextBtn = document.createElement('button');
        nextBtn.className = 'month-calendar-nav-btn';
        nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
        nextBtn.title = "下个月";
        nextBtn.addEventListener('click', () => {
            this.currentMonth++;
            if (this.currentMonth > 11) {
                this.currentMonth = 0;
                this.currentYear++;
            }
            this.draw();
        });
        
        nav.appendChild(prevBtn);
        nav.appendChild(nextBtn);
        header.appendChild(title);
        header.appendChild(nav);
        calendarContainer.appendChild(header);
        
        // 星期栏
        const grid = document.createElement('div');
        grid.className = 'month-calendar-grid';
        
        const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
        weekdays.forEach(day => {
            const el = document.createElement('div');
            el.className = 'month-calendar-weekday';
            el.textContent = day;
            grid.appendChild(el);
        });
        
        // 计算月度日期边界
        const firstDayDate = new Date(this.currentYear, this.currentMonth, 1);
        const startDayOfWeek = firstDayDate.getDay(); // 0-6
        const lastDayDate = new Date(this.currentYear, this.currentMonth + 1, 0);
        const totalDays = lastDayDate.getDate();
        
        // 1. 补足上月残余天数
        const prevMonthLastDate = new Date(this.currentYear, this.currentMonth, 0).getDate();
        for (let i = startDayOfWeek - 1; i >= 0; i--) {
            const cell = document.createElement('div');
            cell.className = 'month-calendar-cell other-month';
            const dayNum = prevMonthLastDate - i;
            cell.innerHTML = `<span class="month-calendar-daynum">${dayNum}</span>`;
            grid.appendChild(cell);
        }
        
        const today = new Date();
        const isTodayYearMonth = today.getFullYear() === this.currentYear && today.getMonth() === this.currentMonth;
        
        // 2. 渲染本月天数并匹配跨天活动
        for (let day = 1; day <= totalDays; day++) {
            const cellDate = new Date(this.currentYear, this.currentMonth, day);
            const cellDayOfWeek = cellDate.getDay();
            
            const cellDateStr = cellDate.getFullYear() + '-' + 
                String(cellDate.getMonth() + 1).padStart(2, '0') + '-' + 
                String(cellDate.getDate()).padStart(2, '0');
            
            const cell = document.createElement('div');
            const isToday = isTodayYearMonth && today.getDate() === day;
            cell.className = `month-calendar-cell current-month ${isToday ? 'today' : ''}`;
            
            const dayNumEl = document.createElement('span');
            dayNumEl.className = 'month-calendar-daynum';
            dayNumEl.textContent = day;
            cell.appendChild(dayNumEl);
            
            // 过滤落在 [date_start, date_end] 范围内的活动
            const dayEvents = this.events.filter(event => {
                const start = event.date_start || event.date;
                const end = event.date_end || event.date;
                return start <= cellDateStr && cellDateStr <= end;
            });
            
            // 每天的格子活动：按 ai_score 从大到小排序，且仅展示评分最高的 7 个
            dayEvents.sort((a, b) => (b.ai_score || 0) - (a.ai_score || 0));
            const topEvents = dayEvents.slice(0, 7);
            
            const eventsContainer = document.createElement('div');
            eventsContainer.className = 'month-calendar-events';
            
            topEvents.forEach(event => {
                const pill = document.createElement('div');
                pill.className = `month-calendar-event-pill type-${event.type || 'default'}`;
                
                // 判断跨天圆角连续感
                const start = event.date_start || event.date;
                const end = event.date_end || event.date;
                
                const isStart = start === cellDateStr;
                const isEnd = end === cellDateStr;
                const isSunday = cellDayOfWeek === 0;
                const isSaturday = cellDayOfWeek === 6;
                
                const leftRound = isStart || isSunday;
                const rightRound = isEnd || isSaturday;
                
                pill.style.borderTopLeftRadius = leftRound ? '4px' : '0px';
                pill.style.borderBottomLeftRadius = leftRound ? '4px' : '0px';
                pill.style.borderTopRightRadius = rightRound ? '4px' : '0px';
                pill.style.borderBottomRightRadius = rightRound ? '4px' : '0px';
                
                // 如果不是首日且不是周日，则只做连线，隐藏胶囊内文字，提升美观度
                if (!isStart && !isSunday) {
                    pill.innerHTML = '&nbsp;';
                } else {
                    const titleStr = event.title_zh || event.title_ja || '活动';
                    pill.textContent = titleStr.length > 5 ? titleStr.substring(0, 5) : titleStr;
                }
                
                // Hover 提示完整信息（包含可读时间范围）
                const scoreText = event.ai_score ? `【评分: ${event.ai_score}分】` : '';
                const periodText = event.event_period ? `[期间: ${event.event_period}] ` : '';
                const titleStr = event.title_zh || event.title_ja || '活动';
                pill.title = `${scoreText}${periodText}${titleStr}\n点击查看详情`;
                
                pill.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (window.showEventModal) {
                        window.showEventModal(event);
                    }
                });
                eventsContainer.appendChild(pill);
            });
            
            cell.appendChild(eventsContainer);
            
            if (topEvents.length > 0) {
                cell.style.cursor = 'pointer';
                cell.addEventListener('click', () => {
                    if (window.showEventModal) {
                        window.showEventModal(topEvents[0]);
                    }
                });
            }
            
            grid.appendChild(cell);
        }
        
        // 3. 补足下月的残余天数使网格铺满整周
        const currentCellsCount = startDayOfWeek + totalDays;
        const remainingCells = (7 - (currentCellsCount % 7)) % 7;
        for (let i = 1; i <= remainingCells; i++) {
            const cell = document.createElement('div');
            cell.className = 'month-calendar-cell other-month';
            cell.innerHTML = `<span class="month-calendar-daynum">${i}</span>`;
            grid.appendChild(cell);
        }
        
        calendarContainer.appendChild(grid);
        container.appendChild(calendarContainer);
    }
};

window.GroupView = {
    renderByType: function(events, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const grouped = {};
        events.forEach(event => {
            const t = event.type || 'other';
            if (!grouped[t]) grouped[t] = [];
            grouped[t].push(event);
        });
        
        container.innerHTML = '<div class="group-wrapper"></div>';
        const wrapper = container.querySelector('.group-wrapper');
        
        const typeMap = {
            'outdoor': '自然户外', 'arts': '手工艺术', 'science': '科学体验',
            'sports': '运动竞技', 'culture': '文化节庆', 'nature': '自然农场',
            'museum': '博物展览', 'performance': '演出舞台', 'other': '其他'
        };
        
        Object.keys(grouped).forEach(type => {
            // 对当前分类下的活动按 AI 评分降序排列 (从高分到低分)
            grouped[type].sort((a, b) => (b.ai_score || 0) - (a.ai_score || 0));

            const typeSection = document.createElement('div');
            typeSection.className = 'group-section';
            typeSection.innerHTML = `<h3 class="group-header type-${type}-text">${typeMap[type] || type} <span class="count">(${grouped[type].length})</span></h3>`;
            
            const list = document.createElement('div');
            list.className = 'group-list';
            grouped[type].forEach(event => {
                const item = document.createElement('div');
                // 增加类型特定的 class 用于常驻色彩标签渲染
                item.className = `group-item type-${event.type || 'default'}`;
                
                const dateStr = window.formatEventDate ? window.formatEventDate(event.date_start, event.date_end, event.event_period || event.date) : (event.event_period || event.date || '未知');
                const scoreStr = event.ai_score ? ` (评分: ${event.ai_score}分)` : '';
                
                item.innerHTML = `
                    <span class="group-item-title">${event.title_zh || event.title_ja}</span>
                    <div class="group-item-actions">
                        <span class="group-item-date">${dateStr}${scoreStr}</span>
                        ${event.source_url ? `
                            <a href="${event.source_url}" target="_blank" class="group-link-btn" title="查看官方页面" onclick="event.stopPropagation();">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                        ` : ''}
                    </div>
                `;
                
                item.addEventListener('click', (e) => {
                    if (e.target.closest('.group-link-btn')) return;
                    if (window.showEventModal) {
                        window.showEventModal(event);
                    }
                });
                list.appendChild(item);
            });
            
            typeSection.appendChild(list);
            wrapper.appendChild(typeSection);
        });
    },
    
    renderByAge: function(events, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const grouped = {
            '0-2': [], '3-5': [], '6-10': [], '11+': []
        };
        
        events.forEach(event => {
            const min = event.age_min !== undefined ? event.age_min : 0;
            const max = event.age_max !== undefined ? event.age_max : 18;
            
            if (min <= 2) grouped['0-2'].push(event);
            if (min <= 5 && max >= 3) grouped['3-5'].push(event);
            if (min <= 10 && max >= 6) grouped['6-10'].push(event);
            if (max >= 11) grouped['11+'].push(event);
        });
        
        container.innerHTML = '<div class="group-wrapper"></div>';
        const wrapper = container.querySelector('.group-wrapper');
        
        const ageNames = {
            '0-2': '0-2岁 (婴幼儿)', '3-5': '3-5岁 (学龄前)', 
            '6-10': '6-10岁 (小学生)', '11+': '11岁以上'
        };
        
        Object.keys(grouped).forEach(age => {
            if (grouped[age].length === 0) return;
            
            // 排序按 AI 评分降序排列 (从高分到低分)
            grouped[age].sort((a, b) => (b.ai_score || 0) - (a.ai_score || 0));

            const section = document.createElement('div');
            section.className = 'group-section';
            section.innerHTML = `<h3 class="group-header age-text">${ageNames[age]} <span class="count">(${grouped[age].length})</span></h3>`;
            
            const list = document.createElement('div');
            list.className = 'group-list';
            grouped[age].forEach(event => {
                const item = document.createElement('div');
                // 增加类型特定的 class 用于常驻色彩标签渲染
                item.className = `group-item type-${event.type || 'default'}`;
                
                const dateStr = window.formatEventDate ? window.formatEventDate(event.date_start, event.date_end, event.event_period || event.date) : (event.event_period || event.date || '未知');
                const scoreStr = event.ai_score ? ` (评分: ${event.ai_score}分)` : '';
                
                item.innerHTML = `
                    <span class="group-item-title">${event.title_zh || event.title_ja}</span>
                    <div class="group-item-actions">
                        <span class="group-item-date">${dateStr}${scoreStr}</span>
                        ${event.source_url ? `
                            <a href="${event.source_url}" target="_blank" class="group-link-btn" title="查看官方页面" onclick="event.stopPropagation();">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                        ` : ''}
                    </div>
                `;
                
                item.addEventListener('click', (e) => {
                    if (e.target.closest('.group-link-btn')) return;
                    if (window.showEventModal) {
                        window.showEventModal(event);
                    }
                });
                list.appendChild(item);
            });
            
            section.appendChild(list);
            wrapper.appendChild(section);
        });
    }
};

// calendar.js
window.CalendarView = {
    render: function(events, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = '';
        
        // Group events by date
        const eventsByDate = {};
        events.forEach(event => {
            if (!event.date) return;
            if (!eventsByDate[event.date]) {
                eventsByDate[event.date] = [];
            }
            eventsByDate[event.date].push(event);
        });
        
        // Get unique dates sorted
        const dates = Object.keys(eventsByDate).sort();
        
        if (dates.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>所选范围内没有活动数据</p></div>';
            return;
        }
        
        const calendarWrapper = document.createElement('div');
        calendarWrapper.className = 'calendar-wrapper';
        
        // Simplified agenda view: a list of dates with events under each
        dates.forEach(date => {
            const dayEvents = eventsByDate[date];
            const dateObj = new Date(date);
            const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
            
            const daySection = document.createElement('div');
            daySection.className = `calendar-day ${isWeekend ? 'weekend' : ''}`;
            
            daySection.innerHTML = `
                <div class="calendar-date-header">
                    <h3>${date}</h3>
                    <span class="day-of-week">${['周日','周一','周二','周三','周四','周五','周六'][dateObj.getDay()]}</span>
                </div>
                <div class="calendar-events">
                    ${dayEvents.map(event => `
                        <div class="calendar-event-item type-${event.type || 'default'}">
                            <span class="event-time">${event.time_start || '全天'}</span>
                            <span class="event-title">${event.title_zh || event.title_ja}</span>
                            ${event.ward ? `<span class="event-ward">${event.ward}</span>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
            calendarWrapper.appendChild(daySection);
        });
        
        container.appendChild(calendarWrapper);
    }
};

window.GroupView = {
    renderByType: function(events, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Group by type
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
            const typeSection = document.createElement('div');
            typeSection.className = 'group-section';
            typeSection.innerHTML = `<h3 class="group-header type-${type}-text">${typeMap[type] || type} <span class="count">(${grouped[type].length})</span></h3>`;
            
            const list = document.createElement('div');
            list.className = 'group-list';
            grouped[type].forEach(event => {
                list.innerHTML += `<div class="group-item">${event.title_zh || event.title_ja} - <small>${event.date || '未知日期'}</small></div>`;
            });
            
            typeSection.appendChild(list);
            wrapper.appendChild(typeSection);
        });
    },
    
    renderByAge: function(events, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Group by age buckets
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
            
            const section = document.createElement('div');
            section.className = 'group-section';
            section.innerHTML = `<h3 class="group-header age-text">${ageNames[age]} <span class="count">(${grouped[age].length})</span></h3>`;
            
            const list = document.createElement('div');
            list.className = 'group-list';
            grouped[age].forEach(event => {
                list.innerHTML += `<div class="group-item">${event.title_zh || event.title_ja} - <small>${event.date || '未知日期'}</small></div>`;
            });
            
            section.appendChild(list);
            wrapper.appendChild(section);
        });
    }
};

class AutoSignIn:
    plugin_name = '站点自动签到'
    plugin_desc = '自动模拟登录、签到站点。'
    plugin_icon = 'signin.png'
    plugin_version = '2.9.15'
    plugin_author = 'thsrite'
    author_url = 'https://github.com/thsrite'
    plugin_config_prefix = 'autosignin_'
    plugin_order = 0
    auth_level = 2
    _ALL_SITES = 'all'
    _HISTORY_DAYS = 14
    _RANDOM_SCHEDULE_KEY = 'random_schedule'
    _RANDOM_EXECUTIONS = 2
    _RANDOM_BEGIN_HOUR = 9
    _RANDOM_END_HOUR = 23
    _scheduler: Optional[BackgroundScheduler] = None
    _site_schema: list = []
    _enabled: bool = False
    _cron: str = ''
    _onlyonce: bool = False
    _notify: bool = False
    _queue_cnt: int = 5
    _sign_sites: list = []
    _login_sites: list = []
    _retry_keyword = None
    _clean: bool = False
    _start_time: int = None
    _end_time: int = None
    _auto_cf: int = 0

    def _resolve_site_ids(self, selected: list) -> list:
        """为详情页展开全选标记，包含内置站点和已启用的自定义站点。"""
        if self._ALL_SITES in selected:
            return [site.id for site in SiteOper().list_order_by_pri()] + [site.get('id') for site in self.__custom_sites()]
        return selected

    def __custom_sites(self) -> List[Any]:
        """读取已启用的自定义站点插件配置。"""
        custom_sites = []
        custom_sites_config = self.get_config('CustomSites')
        if custom_sites_config and custom_sites_config.get('enabled'):
            custom_sites = custom_sites_config.get('sites')
        return custom_sites

    def get_page(self) -> List[dict]:
        """
        拼装插件详情页面，需要返回页面配置，同时附带数据
        """
        today = datetime.now().date()
        date_list = [today - timedelta(days=i) for i in range(self._HISTORY_DAYS)]
        all_data = {'signin': [], 'login': []}
        sites_info = self._build_sites_info()
        for day in date_list:
            day_str = f'{day.month}月{day.day}日'
            day_formatted = day.strftime('%Y-%m-%d')
            day_data = self.get_data(day_str)
            if day_data:
                if isinstance(day_data, list):
                    for record in day_data:
                        if isinstance(record, dict):
                            record['date'] = day_str
                            record['day_obj'] = day
                            if record.get('site_id') is not None:
                                record['site'] = self._get_site_display_name(record['site_id'], sites_info) or record.get('site')
                            if not record.get('type') and '登录' not in record.get('status', ''):
                                if self._status_meta(record.get('status'))['level'] == 'success':
                                    record['status'] += '（历史结果未确认）'
                            if record.get('type') == '登录' or (not record.get('type') and '登录' in record.get('status', '')):
                                all_data['login'].append(record)
                            else:
                                all_data['signin'].append(record)
                                if record.get('logged_in'):
                                    all_data['login'].append({**record, 'status': '登录成功', 'type': '登录', 'success': True})
            signin_history = self.get_data(key='签到-' + day_formatted)
            if signin_history and isinstance(signin_history, dict):
                done_sites = signin_history.get('do', [])
                retry_sites = signin_history.get('retry', [])
                for site_id in done_sites:
                    site_name = self._get_site_display_name(site_id=site_id, sites_info=sites_info)
                    if not site_name:
                        continue
                    result = (signin_history.get('results') or {}).get(str(site_id))
                    if result:
                        status_text = result.get('message') or '签到结果未确认'
                        if not result.get('success') and (not result.get('logged_in')) and (self._status_meta(status_text)['level'] == 'success'):
                            status_text = f'签到失败：{status_text}'
                        if result.get('success') and '登录成功' in status_text:
                            status_text += '（未执行签到）'
                        if result.get('logged_in'):
                            all_data['login'].append({'site': site_name, 'status': '登录成功', 'date': day_str, 'day_obj': day, 'site_id': site_id})
                    elif any((record.get('site') == site_name and record.get('date') == day_str for record in all_data['signin'])):
                        continue
                    elif site_id in retry_sites:
                        status_text = '需要重试'
                    else:
                        status_text = '签到结果未确认'
                    all_data['signin'].append({'site': site_name, 'status': status_text, 'date': day_str, 'day_obj': day, 'site_id': site_id})
            login_history = self.get_data(key='登录-' + day_formatted)
            if login_history and isinstance(login_history, dict):
                done_sites = login_history.get('do', [])
                retry_sites = login_history.get('retry', [])
                for site_id in done_sites:
                    site_name = self._get_site_display_name(site_id=site_id, sites_info=sites_info)
                    if not site_name:
                        continue
                    result = (login_history.get('results') or {}).get(str(site_id))
                    if result:
                        status_text = result.get('message') or '登录结果未确认'
                    elif any((record.get('site') == site_name and record.get('date') == day_str for record in all_data['login'])):
                        continue
                    elif site_id in retry_sites:
                        status_text = '登录需要重试'
                    else:
                        status_text = '登录结果未确认'
                    all_data['login'].append({'site': site_name, 'status': status_text, 'date': day_str, 'day_obj': day, 'site_id': site_id})
        if not all_data['signin'] and (not all_data['login']) and (not self._sign_sites) and (not self._login_sites):
            return [{'component': 'VAlert', 'props': {'type': 'info', 'text': '暂无签到数据', 'variant': 'tonal', 'class': 'mt-4', 'prepend-icon': 'mdi-information'}}]
        signin_site_data = {}
        login_site_data = {}
        site_day_records = {}
        for data in all_data['signin']:
            site_name = data.get('site', '未知站点')
            date_str = data.get('date', '')
            site_day_key = f'{site_name}_{date_str}'
            site_day_records[site_day_key] = data
        for key, record in site_day_records.items():
            site_name = record.get('site', '未知站点')
            if site_name not in signin_site_data:
                signin_site_data[site_name] = []
            signin_site_data[site_name].append(record)
        site_day_records = {}
        for data in all_data['login']:
            site_name = data.get('site', '未知站点')
            date_str = data.get('date', '')
            site_day_key = f'{site_name}_{date_str}'
            site_day_records[site_day_key] = data
        for key, record in site_day_records.items():
            site_name = record.get('site', '未知站点')
            if site_name not in login_site_data:
                login_site_data[site_name] = []
            login_site_data[site_name].append(record)
        for site_id in self._resolve_site_ids(self._sign_sites):
            site_name = self._get_site_display_name(site_id=site_id, sites_info=sites_info)
            if not site_name:
                continue
            signin_site_data.setdefault(site_name, [])
        for site_id in self._resolve_site_ids(self._login_sites):
            site_name = self._get_site_display_name(site_id=site_id, sites_info=sites_info)
            if not site_name:
                continue
            login_site_data.setdefault(site_name, [])
        display_dates = date_list[:7]
        today_label = self._date_label(day=date_list[0])
        signin_stats = self._calculate_day_stats(site_data=signin_site_data, date_label=today_label)
        login_stats = self._calculate_day_stats(site_data=login_site_data, date_label=today_label)
        return [{'component': 'style', 'text': '\n                .autosignin-page {\n                    display: flex;\n                    flex-direction: column;\n                    gap: 12px;\n                }\n                .autosignin-summary {\n                    display: grid;\n                    grid-template-columns: repeat(4, minmax(0, 1fr));\n                    gap: 8px;\n                }\n                .autosignin-stat {\n                    min-width: 0;\n                    padding: 10px 12px;\n                }\n                .autosignin-stat__head {\n                    display: flex;\n                    align-items: center;\n                    gap: 6px;\n                    min-width: 0;\n                    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));\n                    font-size: .75rem;\n                    font-weight: 600;\n                    line-height: 1.25;\n                    overflow: hidden;\n                    text-overflow: ellipsis;\n                    white-space: nowrap;\n                }\n                .autosignin-stat__head .v-icon {\n                    color: rgb(var(--app-card-accent-rgb));\n                }\n                .autosignin-stat__value {\n                    margin-top: 8px;\n                    font-size: 1.25rem;\n                    font-weight: 700;\n                    line-height: 1;\n                    letter-spacing: 0;\n                }\n                .autosignin-stat__meta {\n                    margin-top: 4px;\n                    color: rgba(var(--v-theme-on-surface), .56);\n                    font-size: .72rem;\n                    line-height: 1.25;\n                    white-space: nowrap;\n                    overflow: hidden;\n                    text-overflow: ellipsis;\n                }\n                .autosignin-section {\n                    min-width: 0;\n                }\n                .autosignin-section-head {\n                    display: flex;\n                    align-items: center;\n                    gap: 8px;\n                    min-height: 30px;\n                    margin-bottom: 6px;\n                }\n                .autosignin-section-title {\n                    font-size: .95rem;\n                    font-weight: 700;\n                    letter-spacing: 0;\n                }\n                .autosignin-table-wrap {\n                    overflow-x: auto;\n                    border: 1px solid rgba(var(--v-theme-on-surface), .08);\n                    border-radius: 8px;\n                }\n                .autosignin-table {\n                    min-width: 620px;\n                }\n                html[data-theme="transparent"] .autosignin-table-wrap,\n                .v-theme--transparent .autosignin-table-wrap {\n                    backdrop-filter: blur(var(--transparent-blur, 10px));\n                    background-color: rgba(var(--v-theme-surface), 0) !important;\n                }\n                html[data-theme="transparent"] .autosignin-table,\n                html[data-theme="transparent"] .autosignin-table .v-table__wrapper,\n                html[data-theme="transparent"] .autosignin-table table,\n                html[data-theme="transparent"] .autosignin-table tbody tr,\n                .v-theme--transparent .autosignin-table,\n                .v-theme--transparent .autosignin-table .v-table__wrapper,\n                .v-theme--transparent .autosignin-table table,\n                .v-theme--transparent .autosignin-table tbody tr {\n                    background-color: transparent !important;\n                }\n                .autosignin-table th {\n                    height: 34px !important;\n                    padding: 0 8px !important;\n                    color: rgba(var(--v-theme-on-surface), .62);\n                    font-size: .75rem;\n                    font-weight: 600 !important;\n                    white-space: nowrap;\n                }\n                .autosignin-table td {\n                    height: 38px !important;\n                    padding: 0 8px !important;\n                    vertical-align: middle;\n                }\n                .autosignin-table tbody tr:last-child td {\n                    border-bottom: 0 !important;\n                }\n                .autosignin-site-name {\n                    max-width: 160px;\n                    overflow: hidden;\n                    text-overflow: ellipsis;\n                    white-space: nowrap;\n                    font-weight: 600;\n                    line-height: 1.2;\n                }\n                .autosignin-site-meta {\n                    margin-top: 2px;\n                    color: rgba(var(--v-theme-on-surface), .52);\n                    font-size: .68rem;\n                    line-height: 1.1;\n                }\n                .autosignin-status-cell {\n                    min-width: 92px;\n                }\n                .autosignin-dot-cell {\n                    width: 40px;\n                    text-align: center;\n                }\n                .autosignin-dot {\n                    width: 22px;\n                    height: 22px;\n                    display: inline-flex;\n                    align-items: center;\n                    justify-content: center;\n                    border-radius: 999px;\n                    border: 1px solid transparent;\n                    font-weight: 700;\n                }\n                .autosignin-dot .v-icon {\n                    opacity: 1;\n                }\n                .autosignin-dot--success {\n                    color: rgb(var(--v-theme-success));\n                    background: rgba(var(--v-theme-success), .24);\n                    border-color: rgba(var(--v-theme-success), .38);\n                }\n                .autosignin-dot--warning {\n                    color: rgb(var(--v-theme-warning));\n                    background: rgba(var(--v-theme-warning), .30);\n                    border-color: rgba(var(--v-theme-warning), .48);\n                }\n                .autosignin-dot--error {\n                    color: rgb(var(--v-theme-error));\n                    background: rgba(var(--v-theme-error), .26);\n                    border-color: rgba(var(--v-theme-error), .42);\n                }\n                .autosignin-dot--none {\n                    color: rgba(var(--v-theme-on-surface), .68);\n                    background: rgba(var(--v-theme-on-surface), .14);\n                    border-color: rgba(var(--v-theme-on-surface), .22);\n                }\n                @media (max-width: 720px) {\n                    .autosignin-page {\n                        gap: 10px;\n                    }\n                    .autosignin-summary {\n                        grid-template-columns: repeat(2, minmax(0, 1fr));\n                    }\n                    .autosignin-stat {\n                        padding: 8px 10px;\n                    }\n                    .autosignin-stat__value {\n                        font-size: 1.08rem;\n                    }\n                    .autosignin-table {\n                        min-width: 560px;\n                    }\n                    .autosignin-table th,\n                    .autosignin-table td {\n                        padding-left: 6px !important;\n                        padding-right: 6px !important;\n                    }\n                    .autosignin-site-name {\n                        max-width: 126px;\n                    }\n                    .autosignin-dot-cell {\n                        width: 34px;\n                    }\n                }\n                '}, {'component': 'div', 'props': {'class': 'autosignin-page'}, 'content': [self._build_summary(signin_stats=signin_stats, login_stats=login_stats, days=len(date_list)), self._build_status_section(title='签到状态', icon='mdi-calendar-check', site_data=signin_site_data, display_dates=display_dates, empty_text='暂无签到数据'), self._build_status_section(title='登录状态', icon='mdi-login-variant', site_data=login_site_data, display_dates=display_dates, empty_text='暂无登录数据')]}]

    @staticmethod
    def _add_site_info(sites_info: dict, site_id: Any, site_name: Any) -> None:
        """
        记录站点ID到名称的映射，兼容历史记录中ID类型不一致的情况。
        """
        if site_id is None or not site_name:
            return
        sites_info[site_id] = site_name
        sites_info[str(site_id)] = site_name

    def _build_sites_info(self) -> dict:
        """
        汇总系统站点、索引器站点和自定义站点名称，供详情页历史记录反查。
        """
        sites_info = {}
        for site in SitesHelper().get_indexers():
            if not site.get('public'):
                self._add_site_info(sites_info=sites_info, site_id=site.get('id'), site_name=site.get('name'))
        for site in SiteOper().list_order_by_pri():
            self._add_site_info(sites_info=sites_info, site_id=getattr(site, 'id', None), site_name=getattr(site, 'name', None))
        for site in self.__custom_sites():
            self._add_site_info(sites_info=sites_info, site_id=site.get('id'), site_name=site.get('name'))
        return sites_info

    @staticmethod
    def _get_site_display_name(site_id, sites_info: dict) -> Optional[str]:
        """
        根据站点ID获取详情页中展示的站点名称，查不到时返回空值便于跳过。
        """
        site_id_str = str(site_id)
        name = sites_info.get(site_id_str) or sites_info.get(site_id)
        same_name_ids = {str(key) for key, value in sites_info.items() if value == name}
        return f'{name}（{site_id_str}）' if name and len(same_name_ids) > 1 else name

    @staticmethod
    def _status_meta(status_text: str) -> dict:
        """
        将签到或登录状态文本转换为页面展示需要的颜色、图标和排序权重。
        """
        status_text = str(status_text or '').strip()
        if 'Cookie已失效' in status_text or '失效' in status_text:
            return {'level': 'error', 'color': 'error', 'icon': 'mdi-cookie-off', 'label': status_text or 'Cookie失效', 'sort': 0}
        if any((word in status_text for word in ('失败', '错误', '未成功', '未签到', '未簽到'))):
            return {'level': 'error', 'color': 'error', 'icon': 'mdi-alert-circle', 'label': status_text or '失败', 'sort': 0}
        if any((word in status_text for word in ('重试', '未确认', '未执行签到', '仿真签到成功'))):
            return {'level': 'warning', 'color': 'warning', 'icon': 'mdi-refresh', 'label': status_text or '需要重试', 'sort': 1}
        if '成功' in status_text or '已签到' in status_text:
            return {'level': 'success', 'color': 'success', 'icon': 'mdi-check-circle', 'label': status_text or '成功', 'sort': 3}
        if status_text:
            return {'level': 'none', 'color': 'grey', 'icon': 'mdi-help-circle-outline', 'label': status_text, 'sort': 2}
        return {'level': 'none', 'color': 'grey', 'icon': 'mdi-minus-circle-outline', 'label': '未记录', 'sort': 2}

    @staticmethod
    def _latest_record(records: list, date_label: str=None) -> dict:
        """
        获取指定日期或整个记录列表中的最新一条记录。
        """
        filtered_records = records
        if date_label:
            filtered_records = [record for record in records if record.get('date') == date_label]
        if not filtered_records:
            return {}
        try:
            return sorted(filtered_records, key=lambda item: item.get('day_obj', datetime.min.date()), reverse=True)[0]
        except Exception as e:
            logger.debug(f'获取最新记录失败: {str(e)}')
            return filtered_records[0]

    @staticmethod
    def _date_label(day) -> str:
        """
        将日期对象格式化为历史记录使用的月日标签。
        """
        return f'{day.month}月{day.day}日'

    @classmethod
    def _calculate_day_stats(cls, site_data: dict, date_label: str) -> dict:
        """
        统计指定日期下各站点的成功、异常和未记录数量。
        """
        stats = {'total': len(site_data), 'recorded': 0, 'success': 0, 'warning': 0, 'error': 0, 'none': 0}
        for records in site_data.values():
            record = cls._latest_record(records=records, date_label=date_label)
            if not record:
                stats['none'] += 1
                continue
            stats['recorded'] += 1
            level = cls._status_meta(record.get('status', '')).get('level')
            if level in stats:
                stats[level] += 1
        return stats

    @staticmethod
    def _build_stat_item(label: str, value: str, meta: str, color: str, icon: str) -> dict:
        """
        构建顶部紧凑统计块。
        """
        return {'component': 'div', 'props': {'class': 'autosignin-stat app-card-shell app-card-colorful', 'style': f'--app-card-accent-rgb: var(--v-theme-{color});'}, 'content': [{'component': 'div', 'props': {'class': 'autosignin-stat__head'}, 'content': [{'component': 'VIcon', 'props': {'size': 'x-small', 'color': color}, 'text': icon}, {'component': 'span', 'text': label}]}, {'component': 'div', 'props': {'class': f'autosignin-stat__value text-{color}'}, 'text': value}, {'component': 'div', 'props': {'class': 'autosignin-stat__meta'}, 'text': meta}]}

    @classmethod
    def _build_summary(cls, signin_stats: dict, login_stats: dict, days: int) -> dict:
        """
        构建详情页顶部的签到和登录概要。
        """
        signin_total = signin_stats.get('total') or 0
        login_total = login_stats.get('total') or 0
        signin_problem_count = (signin_stats.get('error') or 0) + (signin_stats.get('warning') or 0)
        signin_missing_count = signin_stats.get('none') or 0
        signin_color = 'info'
        if signin_total:
            signin_color = 'success' if not signin_problem_count and (not signin_missing_count) else 'warning'
        if signin_total and signin_stats.get('error'):
            signin_color = 'error'
        return {'component': 'div', 'props': {'class': 'autosignin-summary'}, 'content': [cls._build_stat_item(label='今日签到', value=f"{signin_stats.get('success') or 0}/{signin_total}", meta=f"失败 {signin_stats.get('error') or 0} · 未确认 {signin_stats.get('warning') or 0} · 未记录 {signin_missing_count}", color=signin_color, icon='mdi-calendar-check'), cls._build_stat_item(label='签到未完成', value=str(signin_problem_count), meta=f"失败 {signin_stats.get('error') or 0} · 未确认 {signin_stats.get('warning') or 0}", color='error' if signin_stats.get('error') else 'warning', icon='mdi-alert-circle-outline'), cls._build_stat_item(label='今日登录', value=f"{login_stats.get('success') or 0}/{login_total}", meta=f"异常 {(login_stats.get('error') or 0) + (login_stats.get('warning') or 0)} · 未记录 {login_stats.get('none') or 0}", color='success' if login_total and (not login_stats.get('error')) and (not login_stats.get('warning')) else 'info', icon='mdi-login-variant'), cls._build_stat_item(label='历史范围', value=f'{days}天', meta='矩阵显示最近7天', color='info', icon='mdi-history')]}

    @classmethod
    def _build_status_section(cls, title: str, icon: str, site_data: dict, display_dates: list, empty_text: str) -> dict:
        """
        构建签到或登录状态区块，使用按站点排列的紧凑矩阵展示最近状态。
        """
        return {'component': 'div', 'props': {'class': 'autosignin-section'}, 'content': [{'component': 'div', 'props': {'class': 'autosignin-section-head'}, 'content': [{'component': 'VIcon', 'props': {'size': 'small', 'color': 'primary'}, 'text': icon}, {'component': 'span', 'props': {'class': 'autosignin-section-title'}, 'text': title}, {'component': 'VSpacer'}, {'component': 'VChip', 'props': {'size': 'x-small', 'variant': 'tonal', 'color': 'primary'}, 'text': f'{len(site_data)} 个站点'}]}, cls._build_status_table(site_data=site_data, display_dates=display_dates, empty_text=empty_text)]}

    @classmethod
    def _build_status_table(cls, site_data: dict, display_dates: list, empty_text: str) -> dict:
        """
        构建按站点和日期交叉展示的状态表格。
        """
        if not site_data:
            return {'component': 'VAlert', 'props': {'type': 'info', 'text': empty_text, 'variant': 'tonal', 'density': 'compact', 'prepend-icon': 'mdi-information'}}
        table_headers = [{'component': 'th', 'props': {'class': 'text-start'}, 'text': '站点'}, {'component': 'th', 'props': {'class': 'text-start'}, 'text': '今日'}]
        for day in display_dates:
            table_headers.append({'component': 'th', 'props': {'class': 'text-center'}, 'text': f'{day.month}/{day.day}'})
        sorted_sites = sorted(site_data.items(), key=lambda item: cls._site_sort_key(site_name=item[0], records=item[1], display_dates=display_dates))
        table_rows = []
        for site_name, records in sorted_sites:
            table_rows.append(cls._build_status_row(site_name=site_name, records=records, display_dates=display_dates))
        return {'component': 'div', 'props': {'class': 'autosignin-table-wrap'}, 'content': [{'component': 'VTable', 'props': {'hover': True, 'density': 'compact', 'class': 'autosignin-table'}, 'content': [{'component': 'thead', 'content': [{'component': 'tr', 'content': table_headers}]}, {'component': 'tbody', 'content': table_rows}]}]}

    @classmethod
    def _site_sort_key(cls, site_name: str, records: list, display_dates: list) -> tuple:
        """
        生成站点行排序键，让今日异常和未记录站点优先展示。
        """
        today_label = cls._date_label(day=display_dates[0]) if display_dates else ''
        today_record = cls._latest_record(records=records, date_label=today_label)
        latest_record = cls._latest_record(records=records)
        status_meta = cls._status_meta(today_record.get('status', '') if today_record else '')
        latest_day = latest_record.get('day_obj', datetime.min.date()) if latest_record else datetime.min.date()
        return (status_meta.get('sort', 2), -latest_day.toordinal(), site_name)

    @classmethod
    def _build_status_row(cls, site_name: str, records: list, display_dates: list) -> dict:
        """
        构建单个站点在状态矩阵中的一行。
        """
        today_label = cls._date_label(day=display_dates[0]) if display_dates else ''
        today_record = cls._latest_record(records=records, date_label=today_label)
        today_status = today_record.get('status', '') if today_record else ''
        today_meta = cls._status_meta(today_status)
        row_cells = [{'component': 'td', 'content': [{'component': 'div', 'props': {'class': 'autosignin-site-name', 'title': site_name}, 'text': site_name}, {'component': 'div', 'props': {'class': 'autosignin-site-meta'}, 'text': f'{len(records)} 条记录' if records else '暂无记录'}]}, {'component': 'td', 'props': {'class': 'autosignin-status-cell'}, 'content': [{'component': 'VChip', 'props': {'size': 'x-small', 'variant': 'tonal', 'color': today_meta.get('color'), 'prepend-icon': today_meta.get('icon')}, 'text': today_meta.get('label')}]}]
        for day in display_dates:
            date_label = cls._date_label(day=day)
            record = cls._latest_record(records=records, date_label=date_label)
            row_cells.append({'component': 'td', 'props': {'class': 'autosignin-dot-cell'}, 'content': [cls._build_status_dot(record=record, date_label=date_label)]})
        return {'component': 'tr', 'content': row_cells}

    @classmethod
    def _build_status_dot(cls, record: dict, date_label: str) -> dict:
        """
        构建矩阵中单日状态的图标点。
        """
        status_text = record.get('status', '') if record else ''
        status_meta = cls._status_meta(status_text)
        return {'component': 'span', 'props': {'class': f"autosignin-dot autosignin-dot--{status_meta.get('level')}", 'title': f"{date_label} {status_meta.get('label')}"}, 'content': [{'component': 'VIcon', 'props': {'size': 'x-small'}, 'text': status_meta.get('icon')}]}

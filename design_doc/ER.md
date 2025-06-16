erDiagram

  Company {
    bigint id PK "主键"
    varchar domains "律所域名（唯一）"
    varchar name "律所名称"
    varchar company_phone "联系电话"
    varchar company_email "联系邮箱"
    text company_address "地址"
    int scottish_partners "苏格兰合伙人数"
    int total_solicitors "总律师数"
    text areas_of_law "法律领域（JSON数组）"
    int team_count "团队数量"
    bigint update_date "更新时间"
    bigint create_date "创建时间"
  }

  Lawyer {
    bigint id PK "主键"
    bigint company_id FK "所属律所ID"
    varchar email_addresses "邮箱"
    varchar name "姓名"
    text practice_areas "执业领域（JSON数组）"
    text address "地址"
    varchar telephone "电话"
    bigint update_date "更新时间"
    bigint create_date "创建时间"
  }

  Task {
    bigint id PK "主键"
    varchar status "任务状态"
    varchar type "任务类型"
    varchar scrapy_id "爬虫ID"
    bigint start_time "启动时间"
    bigint completion_time "完成时间"
    varchar scrapy_url "爬取地址"
    int scraped_company_count "公司数量"
    int scraped_lawyer_count "律师数量"
    text error_message "错误信息"
    bigint update_date "更新时间"
    bigint create_date "创建时间"
  }

  Company ||--o{ Lawyer : employs

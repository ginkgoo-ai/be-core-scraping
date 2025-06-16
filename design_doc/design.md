## 标准 API 文档与数据模型设计文档

### 一、接口定义规范

#### 通用规范

* 所有接口响应统一使用如下结构：

```json
// 成功响应
{
  "success": true,
  "data": { ... },
 
}

// 失败响应
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  } 
}
```

* 所有请求需携带：

  * `Authorization: Bearer <JWT_TOKEN>`
  * `X-Request-Id: <UUID>`

---

#### 1. 触发爬虫接口

* **接口路径**：`POST {base_URL}/scrapy-trigger`

* **请求参数**：

 | 参数名       | 类型   | 必须 | 说明               | 
 |--------------|--------|------|--------------------|
  | `scrapy_id`  | string | 是   | 爬虫唯一标识       | 
  | `source_url` | string | 是   | 目标爬取地址       |

* **响应示例**：

```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "task_id": "task_20231015001",
    "trigger_time": 1697347200,
    "scrapy_id": "lawyer_scraper_v2",
    "source_url": "https://example.com/lawyers"
  } 
}
```

* **失败示例**：

```json
{
  "code": 400,
  "msg":"{scrapy_id}关联的其他任务尚未结束"
}
```


---

#### 2. CRM 同步接口

* **接口路径**：`POST {base_URL}/sync-trigger`

* **请求参数**： 

| 参数名     | 类型   | 必须 | 说明                     |
 |------------|--------|------|--------------------------| 
 | `sync_type`| string | 是   | 同步类型（`company`/`lawyer`） |

* **成功响应**：

```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "task_id": "sync_20231015001",
    "trigger_time": 1697347200,
    "sync_type": "company"
  } 
}
```

* **失败响应**：

```json

{
  "code": 400,
  "msg":"可同步的数据为:0"
}
```

---

#### 3. 任务状态监测接口

* **接口路径**：`GET {base_URL}/task/{task_id}`

* **成功响应**：

```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "task_id": "task_20231015001",
    "trigger_time": 1697347200,
    "scrapy_id": "lawyer_scraper_v2",
    "source_url": "https://example.com/lawyers",
    "sync_type": "lawyer",
    "status": "COMPLETED",
    "completion_time": 1697348000,
    "task_info": {
      "scraped_company_count": 50,
      "scraped_lawyer_count": 200,
      "error_count": 3
    }
  } 
}
```

* **失败响应**：

```json

{
  "code": 400,
  "msg":"{task_id}对应任务不存在！"
}
```

---

### 二、数据模型定义

#### 1. Company

* **表结构设计**：

 | 字段名           | 类型         | 描述             | 是否唯一 | 示例值                         | 
 |------------------|--------------|------------------|----------|-------------------------------|
| id               | bigint       | 主键             | 是       | 12345                         | 
| domains          | varchar(255) | 律所域名         | 是       | "smithlaw.com,ldn.smithlaw.com" |
| name             | varchar(255) | 律所名称         | 否       | "Smith & Partners Law"        |
| company\_phone    | varchar(20)  | 联系电话         | 否       | "+44 20 1234 5678"             |
| company\_email    | varchar(100) | 联系邮箱         | 否       | "[info@smithlaw.com](mailto:info@smithlaw.com)"           | 
| company\_address  | text         | 地址             | 否       | "123 Law Street, London"      | 
| scottish\_partners| int          | 苏格兰合伙人数   | 否       | 15                            |
| total\_solicitors | int          | 总律师数         | 否       | 100                           |
| areas\_of\_law     | text         | JSON数组（领域） | 否       | ["Commercial", "Family"]     |
| team\_count       | int          | 团队数量         | 否       | 8                             | 
| update\_date      | bigint       | 更新时间         | 否       | 1697347200                    | 
| create\_date      | bigint       | 创建时间         | 否       | 1697347200                    |

* **索引设计**：

  * `UNIQUE INDEX idx_company_domains(domains)`
  * `INDEX idx_company_name(name)`

---

#### 2. Lawyer

* **表结构设计**： 

| 字段名         | 类型         | 描述           | 是否唯一/关联 | 示例值                   |
|----------------|--------------|----------------|----------------|--------------------------|
| id             | bigint       | 主键           | 是             | 98765                    | 
| company\_id     | bigint       | 所属律所 ID    | 外键           | 12345                    | 
| email\_addresses| varchar(100) | 邮箱           | 否             | "[j.doe@smithlaw.com](mailto:j.doe@smithlaw.com)"     | 
| name           | varchar(100) | 姓名           | 否             | "John Doe"               | 
| practice\_areas | text         | JSON数组       | 否             | \["Corporate"]            | 
| address        | text         | 地址           | 否             | "London Office"          | 
| telephone      | varchar(20)  | 电话           | 否             | "+44 7700 900123"         | 
| update\_date    | bigint       | 更新时间       | 否             | 1697347200               | 
| create\_date    | bigint       | 创建时间       | 否             | 1697347200               |

* **外键约束**：

  * `FOREIGN KEY (company_id) REFERENCES Company(id) ON DELETE CASCADE`

---

#### 3. Task

* **表结构设计**： 

| 字段名               | 类型         | 描述               | 枚举/唯一 | 示例值               | 
|----------------------|--------------|--------------------|------------|----------------------| 
| id                   | bigint       | 主键               | 是         | 54321                | 
| status               | varchar(20)  | 任务状态           | 枚举       | "COMPLETED"         | 
| type                 | varchar(30)  | 任务类型           | 枚举       | "scrapy\_lawyer"     | 
| scrapy\_id            | varchar(50)  | 爬虫 ID            | 否         | "lawyer\_scraper\_v2" | 
| start\_time           | bigint       | 启动时间           | 否         | 1697347200           | 
| completion\_time      | bigint       | 完成时间           | 否         | 1697348000           | 
| scrapy\_url           | varchar(255) | 爬取地址           | 否         | "[https://example.com](https://example.com)" | 
| scraped\_company\_count| int          | 公司数量           | 否         | 50                   | 
| scraped\_lawyer\_count | int          | 律师数量           | 否         | 200                  | 
| error\_message        | text         | 错误信息（失败时） | 否         | "连接超时"           | 
| update\_date          | bigint       | 更新时间           | 否         | 1697347200           | 
| create\_date          | bigint       | 创建时间           | 否         | 1697347200           |

* **枚举值定义**：

  * `status`: `IN_PROGRESS` / `COMPLETED` / `CANCELLED` / `FAILED`
  * `type`: `scrapy_company` / `scrapy_lawyer` / `sync_company` / `sync_lawyer`

* **索引设计**：

  * `INDEX idx_task_status_type(status, type)`

---

### 三、业务规则与约束

1. **接口幂等性**：基于 `X-Request-Id` 控制，同一 ID 多次请求 5 分钟内返回相同响应。
2. **数据唯一性**：

   * `Company.domains` 唯一，用于区分律所
   * `Lawyer.email_addresses` 不唯一，支持多个邮箱

---

### 四、安全与性能设计

1. **认证机制**：所有接口需通过 JWT 认证，过期时间待定
2. **数据脱敏**：敏感字段如 `company_phone`、`email` 等根据业务需要脱敏处理
3. **数据库维护**：

   * `Task` 表中状态为 `COMPLETED` 且完成时间超过 30 天的任务，定期清理
   * 合理建立索引，优化查询性能

 


"""
Module cung cấp mockup data để test chức năng phân tích log lỗi pipeline khi không thể truy cập URL.
Dùng cho trường hợp URL pipeline nằm trong mạng nội bộ công ty và không thể truy cập trực tiếp.
"""

# Cấu trúc mock data sẽ giống với định dạng trả về của hàm extract_pipeline_logs
# Mỗi loại mockup sẽ đại diện cho một loại lỗi phổ biến trong pipeline

MOCK_PIPELINE_LOGS = {
    # 1. Lỗi xây dựng (build errors)
    "build_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Scanning for projects...
[INFO] ------------------------------------------------------------------------
[INFO] Building payment-service 1.0.0-SNAPSHOT
[INFO] ------------------------------------------------------------------------
[INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ payment-service ---
[ERROR] /builds/banking/payment-service/src/main/java/com/bank/payment/controller/TransactionController.java:[45,8] cannot find symbol
[ERROR]   symbol:   class PaymentResponse
[ERROR]   location: package com.bank.payment.model
[ERROR] /builds/banking/payment-service/src/main/java/com/bank/payment/service/impl/TransferServiceImpl.java:[72,13] cannot find symbol
[ERROR]   symbol:   method validateTransaction(Transaction)
[ERROR]   location: class com.bank.payment.service.impl.TransferServiceImpl
[INFO] 2 errors 
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project payment-service: Compilation failure
[ERROR] 
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  5.342 s
[INFO] Finished at: 2025-09-21T09:45:23+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "cannot find symbol symbol: class PaymentResponse location: package com.bank.payment.model",
            "cannot find symbol symbol: method validateTransaction(Transaction) location: class com.bank.payment.service.impl.TransferServiceImpl",
            "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project payment-service: Compilation failure"
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/payment-service/-/jobs/12345",
            "https://git.internal.company.vn/banking/payment-service/-/pipelines/6789"
        ]
    },

    # 2. Lỗi cú pháp (syntax error)
    "syntax_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Scanning for projects...
[INFO] ------------------------------------------------------------------------
[INFO] Building customer-service 2.1.0-SNAPSHOT
[INFO] ------------------------------------------------------------------------
[INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ customer-service ---
[ERROR] /builds/banking/customer-service/src/main/java/com/bank/customer/service/CustomerServiceImpl.java:[67,42] ';' expected
[ERROR] /builds/banking/customer-service/src/main/java/com/bank/customer/service/CustomerServiceImpl.java:[112,5] reached end of file while parsing
[INFO] 2 errors 
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project customer-service: Compilation failure
[ERROR] 
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  3.841 s
[INFO] Finished at: 2025-09-21T10:12:45+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "';' expected",
            "reached end of file while parsing",
            "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project customer-service: Compilation failure"
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/customer-service/-/jobs/23456",
            "https://git.internal.company.vn/banking/customer-service/-/pipelines/7890"
        ]
    },

    # 3. Lỗi kiểm thử (test failures)
    "test_failure": {
        "success": True,
        "error": None,
        "logs": """
[INFO] --- maven-surefire-plugin:2.22.2:test (default-test) @ account-service ---
[INFO] Running com.bank.account.service.AccountBalanceServiceTest
[ERROR] Tests run: 5, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 1.257 s <<< FAILURE! - in com.bank.account.service.AccountBalanceServiceTest
[ERROR] testCalculateInterestWithZeroBalance(com.bank.account.service.AccountBalanceServiceTest)  Time elapsed: 0.527 s  <<< FAILURE!
java.lang.AssertionError: 
Expected: <0.0>
     but: was <0.01>
    at org.hamcrest.MatcherAssert.assertThat(MatcherAssert.java:20)
    at org.junit.Assert.assertThat(Assert.java:956)
    at com.bank.account.service.AccountBalanceServiceTest.testCalculateInterestWithZeroBalance(AccountBalanceServiceTest.java:58)

[ERROR] testWithdrawalWithInsufficientFunds(com.bank.account.service.AccountBalanceServiceTest)  Time elapsed: 0.137 s  <<< FAILURE!
java.lang.AssertionError: Expected exception: com.bank.account.exception.InsufficientFundsException

[INFO] Results:
[ERROR] Failures: 
[ERROR]   AccountBalanceServiceTest.testCalculateInterestWithZeroBalance:58 
Expected: <0.0>
     but: was <0.01>
[ERROR]   AccountBalanceServiceTest.testWithdrawalWithInsufficientFunds:78 Expected exception: com.bank.account.exception.InsufficientFundsException
[ERROR] Tests run: 5, Failures: 2, Errors: 0, Skipped: 0
[ERROR] 
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:2.22.2:test (default-test) on project account-service: There are test failures.
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  12.358 s
[INFO] Finished at: 2025-09-21T11:05:32+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Tests run: 5, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 1.257 s <<< FAILURE!",
            "Expected: <0.0> but: was <0.01>",
            "Expected exception: com.bank.account.exception.InsufficientFundsException",
            "Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:2.22.2:test (default-test) on project account-service: There are test failures."
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/account-service/-/jobs/34567",
            "https://git.internal.company.vn/banking/account-service/-/pipelines/8901"
        ]
    },

    # 4. Lỗi cấu hình (configuration errors)
    "config_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Scanning for projects...
[WARNING] Some problems were encountered while building the effective model for com.bank:notification-service:jar:1.0.0
[WARNING] 'dependencies.dependency.(groupId:artifactId:type:classifier)' must be unique: org.springframework.boot:spring-boot-starter-web:jar -> duplicate declaration of version (?) @ line 32, column 21
[ERROR] Error resolving version for plugin 'org.springframework.boot:spring-boot-maven-plugin' from the repositories [central (https://repo.maven.apache.org/maven2, default, releases)]: Plugin not found in any plugin repository
[ERROR] Failed to execute goal on project notification-service: Could not resolve dependencies for project com.bank:notification-service:jar:1.0.0: Could not find artifact com.bank:common-lib:jar:2.1.0 in central (https://repo.maven.apache.org/maven2) -> [Help 1]
[ERROR] 
[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.
[ERROR] Re-run Maven using the -X switch to enable full debug logging.
[ERROR] 
[ERROR] For more information about the errors and possible solutions, please read the following articles:
[ERROR] [Help 1] http://cwiki.apache.org/confluence/display/MAVEN/DependencyResolutionException
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  3.641 s
[INFO] Finished at: 2025-09-21T13:22:17+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Error resolving version for plugin 'org.springframework.boot:spring-boot-maven-plugin' from the repositories",
            "Failed to execute goal on project notification-service: Could not resolve dependencies",
            "Could not find artifact com.bank:common-lib:jar:2.1.0 in central"
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/notification-service/-/jobs/45678",
            "https://git.internal.company.vn/banking/notification-service/-/pipelines/9012"
        ]
    },

    # 5. Lỗi dependency
    "dependency_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Scanning for projects...
[INFO] ------------------------------------------------------------------------
[INFO] Building fraud-detection-service 0.9.0-SNAPSHOT
[INFO] ------------------------------------------------------------------------
[ERROR] [ERROR] Failed to execute goal on project fraud-detection-service: Could not resolve dependencies for project com.bank:fraud-detection-service:jar:0.9.0-SNAPSHOT: The following artifacts could not be resolved: com.bank.ml:prediction-engine:jar:3.2.1, com.bank.security:encryption-lib:jar:1.5.0: Could not find artifact com.bank.ml:prediction-engine:jar:3.2.1 -> [Help 1]
[ERROR] [ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.
[ERROR] [ERROR] Re-run Maven using the -X switch to enable full debug logging.
[ERROR] [ERROR] For more information about the errors and possible solutions, please read the following articles:
[ERROR] [Help 1] http://cwiki.apache.org/confluence/display/MAVEN/DependencyResolutionException
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  2.173 s
[INFO] Finished at: 2025-09-21T14:37:05+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Failed to execute goal on project fraud-detection-service: Could not resolve dependencies",
            "The following artifacts could not be resolved: com.bank.ml:prediction-engine:jar:3.2.1, com.bank.security:encryption-lib:jar:1.5.0",
            "Could not find artifact com.bank.ml:prediction-engine:jar:3.2.1"
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/fraud-detection-service/-/jobs/56789",
            "https://git.internal.company.vn/banking/fraud-detection-service/-/pipelines/1234"
        ]
    },

    # 6. Lỗi triển khai (deployment errors)
    "deployment_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Successfully built image registry.internal.company.vn/banking/online-banking:1.4.2
[INFO] Pushing image to registry...
[INFO] Successfully pushed image registry.internal.company.vn/banking/online-banking:1.4.2
[INFO] Starting deployment to Kubernetes cluster...
[ERROR] Error from server (Forbidden): deployments.apps "online-banking" is forbidden: User "gitlab-runner" cannot update resource "deployments" in API group "apps" in the namespace "production"
[ERROR] Failed to deploy application to Kubernetes cluster
[INFO] Rollback initiated...
[INFO] Rollback completed successfully
[ERROR] The deployment process has failed. Please check Kubernetes permissions and configurations.
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  8.945 s
[INFO] Finished at: 2025-09-21T15:52:41+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Error from server (Forbidden): deployments.apps \"online-banking\" is forbidden: User \"gitlab-runner\" cannot update resource \"deployments\" in API group \"apps\" in the namespace \"production\"",
            "Failed to deploy application to Kubernetes cluster",
            "The deployment process has failed. Please check Kubernetes permissions and configurations."
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/online-banking/-/jobs/67890",
            "https://git.internal.company.vn/banking/online-banking/-/pipelines/2345"
        ]
    },

    # 7. Lỗi Database
    "database_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Executing Flyway database migrations...
[INFO] Flyway Community Edition 8.5.13 by Redgate
[INFO] Database: jdbc:postgresql://db-prod:5432/banking (PostgreSQL 14.4)
[INFO] Successfully validated 15 migrations (execution time 00:00.042s)
[INFO] Current version of schema "public": 7.2
[ERROR] Migration V7_3__Add_transaction_history_table.sql failed
[ERROR] Migration V7_3__Add_transaction_history_table.sql failed
[ERROR] -----------------------------------------------------
[ERROR] SQL State  : 42P07
[ERROR] Error Code : 0
[ERROR] Message    : ERROR: relation "transaction_history" already exists
[ERROR] Location   : db/migration/V7_3__Add_transaction_history_table.sql (/builds/banking/core-banking/target/classes/db/migration/V7_3__Add_transaction_history_table.sql)
[ERROR] Line       : 1
[ERROR] Statement  : CREATE TABLE transaction_history (
    id SERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL,
    amount DECIMAL(19, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
)
[ERROR] Flyway migration failed: Database migration failed
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  4.218 s
[INFO] Finished at: 2025-09-21T16:24:59+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Migration V7_3__Add_transaction_history_table.sql failed",
            "SQL State  : 42P07",
            "Message    : ERROR: relation \"transaction_history\" already exists",
            "Flyway migration failed: Database migration failed"
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/core-banking/-/jobs/78901",
            "https://git.internal.company.vn/banking/core-banking/-/pipelines/3456"
        ]
    },

    # 8. Lỗi phức tạp (nhiều lỗi kết hợp)
    "complex_error": {
        "success": True,
        "error": None,
        "logs": """
[INFO] Scanning for projects...
[INFO] ------------------------------------------------------------------------
[INFO] Building api-gateway 2.5.0-SNAPSHOT
[INFO] ------------------------------------------------------------------------
[WARNING] Some problems were encountered while building the effective model for com.bank:api-gateway:jar:2.5.0-SNAPSHOT
[WARNING] 'dependencies.dependency.(groupId:artifactId:type:classifier)' must be unique: org.springframework.cloud:spring-cloud-starter-gateway:jar -> version 3.1.1 vs 3.0.0 @ line 45, column 21
[ERROR] [ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project api-gateway: Compilation failure: Compilation failure: 
[ERROR] /builds/banking/api-gateway/src/main/java/com/bank/gateway/filter/AuthFilter.java:[34,39] cannot find symbol
[ERROR]   symbol:   method validateToken(java.lang.String)
[ERROR]   location: variable jwtService of type com.bank.security.JwtService
[ERROR] /builds/banking/api-gateway/src/main/java/com/bank/gateway/filter/RateLimitFilter.java:[28,8] '{' expected
[INFO] --- maven-surefire-plugin:2.22.2:test (default-test) @ api-gateway ---
[INFO] Running com.bank.gateway.filter.AuthFilterTest
[ERROR] Tests run: 3, Failures: 1, Errors: 1, Skipped: 0, Time elapsed: 0.753 s <<< FAILURE! - in com.bank.gateway.filter.AuthFilterTest
[ERROR] testInvalidToken(com.bank.gateway.filter.AuthFilterTest)  Time elapsed: 0.241 s  <<< FAILURE!
java.lang.AssertionError: Status expected:<401> but was:<500>
[ERROR] testMissingToken(com.bank.gateway.filter.AuthFilterTest)  Time elapsed: 0.125 s  <<< ERROR!
java.lang.NullPointerException: Cannot invoke "com.bank.security.JwtService.extractUsername(String)" because "this.jwtService" is null
[INFO] Build deploying to Kubernetes...
[ERROR] Error from server (Forbidden): configmaps "api-gateway-config" is forbidden: User "gitlab-runner" cannot create resource "configmaps" in API group "" in the namespace "staging"
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  15.723 s
[INFO] Finished at: 2025-09-21T17:35:12+07:00
[INFO] ------------------------------------------------------------------------
        """,
        "error_lines": [
            "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile (default-compile) on project api-gateway: Compilation failure",
            "cannot find symbol symbol: method validateToken(java.lang.String) location: variable jwtService of type com.bank.security.JwtService",
            "'{' expected",
            "Tests run: 3, Failures: 1, Errors: 1, Skipped: 0",
            "Status expected:<401> but was:<500>",
            "java.lang.NullPointerException: Cannot invoke \"com.bank.security.JwtService.extractUsername(String)\" because \"this.jwtService\" is null",
            "Error from server (Forbidden): configmaps \"api-gateway-config\" is forbidden: User \"gitlab-runner\" cannot create resource \"configmaps\" in API group \"\" in the namespace \"staging\""
        ],
        "job_links": [
            "https://git.internal.company.vn/banking/api-gateway/-/jobs/89012",
            "https://git.internal.company.vn/banking/api-gateway/-/pipelines/4567"
        ]
    }
}

# Hàm trợ giúp để truy cập mockup data như thay thế cho việc truy cập URL thực tế
def get_mock_pipeline_logs(error_type):
    """
    Trả về mock log cho một loại lỗi cụ thể.
    
    Tham số:
        error_type: Loại lỗi muốn lấy mock data (e.g. 'build_error', 'test_failure', etc.)
        
    Trả về:
        Dictionary chứa mock pipeline logs hoặc None nếu không tìm thấy loại lỗi
    """
    return MOCK_PIPELINE_LOGS.get(error_type)

def get_all_mock_error_types():
    """
    Trả về danh sách tất cả các loại lỗi có sẵn trong mock data.
    
    Trả về:
        List các loại lỗi có trong mock data
    """
    return list(MOCK_PIPELINE_LOGS.keys())

# Ví dụ sử dụng:
if __name__ == "__main__":
    # Ví dụ lấy mock data cho lỗi xây dựng
    build_error_logs = get_mock_pipeline_logs("build_error")
    if build_error_logs:
        print(f"=== MOCK LOGS FOR BUILD ERROR ===")
        print(f"Success: {build_error_logs['success']}")
        print(f"Error Lines: {len(build_error_logs['error_lines'])}")
        for i, line in enumerate(build_error_logs['error_lines']):
            print(f"{i+1}. {line}")
        print("\n")
    
    # Liệt kê tất cả các loại lỗi có sẵn
    print(f"Available error types: {get_all_mock_error_types()}")

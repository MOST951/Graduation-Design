package com.weibo.web.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.tags.Tag;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;

/**
 * API文档配置。
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        final String securitySchemeName = "bearerAuth";
        return new OpenAPI()
            .addSecurityItem(new SecurityRequirement().addList(securitySchemeName))
            .components(
                new Components()
                    .addSecuritySchemes(securitySchemeName,
                        new SecurityScheme()
                            .name(securitySchemeName)
                            .type(SecurityScheme.Type.HTTP)
                            .scheme("bearer")
                            .bearerFormat("JWT")
                    )
            )
            .info(new Info()
                .title("\u5FAE\u535A\u8206\u60C5\u5206\u6790\u7CFB\u7EDF - Java \u540E\u7AEF API")
                .description(
                    "\u57FA\u4E8E Spring Boot \u7684\u5FAE\u535A\u8206\u60C5\u60C5\u611F\u5206\u6790\u7CFB\u7EDF Java \u540E\u7AEF\n\n"
                    + "**\u8BBA\u6587 6.2.2**: \u8D1F\u8D23\u7528\u6237\u8BA4\u8BC1\u3001\u4EFB\u52A1\u7BA1\u7406\u3001\u4EEA\u8868\u76D8\u3001\u76D1\u63A7\u3001\u6D41\u6C34\u7EBF\u7BA1\u7406.\n\n"
                    + "**\u53CC\u540E\u7AEF\u534F\u540C (6.2.3)**: \u7528\u6237/\u4EFB\u52A1/\u4EEA\u8868\u76D8\u8D70\u672C\u670D\u52A1 (8081); "
                    + "\u722C\u866B/\u60C5\u611F\u5206\u6790/Spark\u8D70 Flask (5000).")
                .version("2.0.0")
                .contact(new Contact().name("\u7F57\u68EE / 2022407443"))
            )
            .tags(Arrays.asList(
                new Tag().name("auth-controller").description("\u7528\u6237\u8BA4\u8BC1 - \u767B\u5F55/\u6CE8\u518C/JWT (\u8BBA\u6587 6.1.8)"),
                new Tag().name("dashboard-controller").description("\u53EF\u89C6\u5316\u4EEA\u8868\u76D8 - \u7EDF\u8BA1/\u5206\u5E03/\u8D8B\u52BF (\u8BBA\u6587 6.1.7)"),
                new Tag().name("collection-controller").description("\u6570\u636E\u91C7\u96C6\u4EFB\u52A1\u7BA1\u7406 (\u8BBA\u6587 6.1.1)"),
                new Tag().name("analysis-controller").description("\u60C5\u611F\u5206\u6790\u7ED3\u679C\u67E5\u8BE2 (\u8BBA\u6587 4.2.1)"),
                new Tag().name("monitor-controller").description("\u5B9E\u65F6\u8206\u60C5\u76D1\u63A7 (\u8BBA\u6587 6.1.5)"),
                new Tag().name("pipeline-controller").description("\u6570\u636E\u6D41\u6C34\u7EBF\u7BA1\u7406 (\u8BBA\u6587 6.1.6)"),
                new Tag().name("admin-controller").description("\u7CFB\u7EDF\u7BA1\u7406 - \u7528\u6237/\u914D\u7F6E/\u65E5\u5FD7 (\u8BBA\u6587 6.1.8)"),
                new Tag().name("user-tags-controller").description("\u7528\u6237\u884C\u4E3A\u5206\u6790 - \u6807\u7B7E/\u753B\u50CF"),
                new Tag().name("weibo-misc-controller").description("\u4E09\u7EF4\u5EA6\u6392\u5E8F + \u4F20\u64AD\u7F51\u7EDC (\u8BBA\u6587 4.2.2)")
            ));
    }
}

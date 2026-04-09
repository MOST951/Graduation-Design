package com.weibo.web.mapper;

import com.weibo.web.dto.response.AnalysisResponse;
import com.weibo.web.entity.SentimentResult;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

/**
 * 使用MapStruct进行SentimentResult实体和DTO之间的转换。
 */
@Mapper(componentModel = "spring")
public interface SentimentResultMapper {

    SentimentResultMapper INSTANCE = Mappers.getMapper(SentimentResultMapper.class);

    AnalysisResponse toDto(SentimentResult entity);
}

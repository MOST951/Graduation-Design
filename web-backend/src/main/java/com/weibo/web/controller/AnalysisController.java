package com.weibo.web.controller;

import com.weibo.common.model.ResponseResult;
import com.weibo.web.anno.RateLimit;
import com.weibo.web.dto.response.AnalysisResponse;
import com.weibo.web.dto.response.PageResponse;
import com.weibo.web.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisService analysisService;

    @GetMapping("/results/{taskId}")
    @RateLimit(count = 10, time = 60)
    public ResponseResult<PageResponse<AnalysisResponse>> getResults(
            @PathVariable Long taskId, Pageable pageable) {
        return ResponseResult.success(analysisService.getResults(taskId, pageable));
    }
}

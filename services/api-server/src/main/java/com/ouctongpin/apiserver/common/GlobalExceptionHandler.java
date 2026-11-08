package com.ouctongpin.apiserver.common;

import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    // Preserve moderation's 422/503 instead of converting them into an HTTP 200 error envelope.
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Result<?>> handleResponseStatusException(ResponseStatusException e) {
        int status = e.getStatusCode().value();
        String message = switch (status) {
            case 422 -> "内容未通过安全检查";
            case 503 -> "内容安全服务暂不可用，请稍后重试";
            default -> "请求未通过检查";
        };
        return ResponseEntity.status(e.getStatusCode()).body(Result.fail(status, message));
    }

    // 拦截 @Valid 校验失败抛出的异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<?> handleValidException(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldError().getDefaultMessage();
        return Result.fail(1001, msg);
    }

    // 拦截系统内部其他异常
    @ExceptionHandler(Exception.class)
    public Result<?> handleException(Exception e) {
        return Result.fail(500, "服务器内部错误");
    }
}

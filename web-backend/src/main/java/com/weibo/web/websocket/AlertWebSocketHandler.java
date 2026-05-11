package com.weibo.web.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArraySet;

@Slf4j
public class AlertWebSocketHandler extends TextWebSocketHandler {

    private static final CopyOnWriteArraySet<WebSocketSession> sessions = new CopyOnWriteArraySet<>();
    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
        log.info("WebSocket connected: {}, total sessions: {}", session.getId(), sessions.size());
        try {
            Map<String, Object> welcome = new LinkedHashMap<>();
            welcome.put("type", "connection");
            welcome.put("message", "Connected to alert WebSocket");
            welcome.put("timestamp", LocalDateTime.now().toString());
            session.sendMessage(new TextMessage(objectMapper.writeValueAsString(welcome)));
        } catch (IOException e) {
            log.error("Failed to send welcome message", e);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
        log.info("WebSocket disconnected: {}, remaining sessions: {}", session.getId(), sessions.size());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("type", "echo");
        response.put("data", message.getPayload());
        response.put("timestamp", LocalDateTime.now().toString());
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(response)));
    }

    public static void broadcast(String type, Object data) {
        Map<String, Object> msg = new LinkedHashMap<>();
        msg.put("type", type);
        msg.put("data", data);
        msg.put("timestamp", LocalDateTime.now().toString());
        try {
            String json = objectMapper.writeValueAsString(msg);
            TextMessage textMessage = new TextMessage(json);
            for (WebSocketSession session : sessions) {
                if (session.isOpen()) {
                    session.sendMessage(textMessage);
                }
            }
        } catch (IOException e) {
            log.error("Failed to broadcast message", e);
        }
    }
}

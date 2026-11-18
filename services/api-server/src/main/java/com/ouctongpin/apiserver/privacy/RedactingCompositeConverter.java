package com.ouctongpin.apiserver.privacy;

import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.pattern.CompositeConverter;

/** Wrap the entire output, including exception text, instead of only the message. */
public class RedactingCompositeConverter extends CompositeConverter<ILoggingEvent> {
    @Override
    protected String transform(ILoggingEvent event, String output) {
        return LogRedactor.redact(output);
    }
}

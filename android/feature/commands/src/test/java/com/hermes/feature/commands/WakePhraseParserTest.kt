package com.hermes.feature.commands

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNull
import org.junit.Test

class WakePhraseParserTest {
    @Test
    fun parse_accepts_only_explicit_wake_phrase_at_start() {
        assertEquals("ping no pc-casa", WakePhraseParser.parse("Ei Jarvis, ping no PC-Casa"))
        assertEquals("ping no pc-casa", WakePhraseParser.parse("Jarvis, ping no PC-Casa"))
    }

    @Test
    fun parse_ignores_ambient_text_without_wake_phrase() {
        assertNull(WakePhraseParser.parse("ping no PC-Casa"))
        assertNull(WakePhraseParser.parse("o Jarvis está ouvindo"))
        assertNull(WakePhraseParser.parse("fala comigo"))
        assertNull(WakePhraseParser.parse("Javrvis, ping no PC-Casa"))
        assertNull(WakePhraseParser.parse("Ei Jarvis"))
        assertNull(WakePhraseParser.parse("Jarvis"))
        assertTrue(WakePhraseParser.isWakeOnly("Ei Jarvis"))
        assertTrue(WakePhraseParser.isWakeOnly("Jarvis"))
    }
}

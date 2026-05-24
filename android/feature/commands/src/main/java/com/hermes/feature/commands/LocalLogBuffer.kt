package com.hermes.feature.commands

import android.content.Context
import java.io.File
import java.util.ArrayDeque

class LocalLogBuffer(context: Context, private val maxLines: Int = 200) {
    private val file = File(context.filesDir, "hermes_logs.txt")
    private val deque = ArrayDeque<String>()

    @Synchronized
    fun append(line: String) {
        val stamp = "${System.currentTimeMillis()}: $line"
        deque.addLast(stamp)
        while (deque.size > maxLines) deque.removeFirst()
        runCatching { file.appendText(stamp + "\n") }
    }

    @Synchronized
    fun snapshot(): List<String> = deque.toList()
}

import type {
  InteractionEvent,
  InteractionPattern,
  LanguageStyle
} from '../types';

export class InteractionHistoryAnalyzer {
  analyze(events: InteractionEvent[]): InteractionPattern {
    if (events.length === 0) {
      return {
        preferredLanguageStyle: 'formal' as LanguageStyle,
        averageResponseDetailPreference: 0.5,
        suggestionAcceptanceRate: 0.5,
        preferredResponseSpeed: 'moderate',
        technicalInterestLevel: 0.5
      };
    }

    const languageStyleCounts: Record<LanguageStyle, number> = {
      formal: 0,
      casual: 0
    };

    let totalResponseDetail = 0;
    let suggestionAccepts = 0;
    let suggestionRejects = 0;
    let totalResponseTime = 0;
    let technicalInterestSum = 0;

    for (const event of events) {
      languageStyleCounts[event.languageStyle]++;
      totalResponseDetail += event.contentLength;
      totalResponseTime += event.responseTime;

      if (event.eventType === 'suggestion_accept') {
        suggestionAccepts++;
      } else if (event.eventType === 'suggestion_reject') {
        suggestionRejects++;
      }

      technicalInterestSum += event.contentLength;
    }

    const totalEvents = events.length;
    const preferredLanguageStyle =
      (languageStyleCounts.formal > languageStyleCounts.casual ? 'formal' : 'casual') as LanguageStyle;

    const averageResponseDetailPreference = Math.min(
      totalResponseDetail / (totalEvents * 100),
      1
    );

    const suggestionAcceptanceRate =
      suggestionAccepts + suggestionRejects > 0
        ? suggestionAccepts / (suggestionAccepts + suggestionRejects)
        : 0.5;

    const avgResponseTime = totalResponseTime / totalEvents;
    let preferredResponseSpeed: 'fast' | 'moderate' | 'slow';
    if (avgResponseTime < 1000) {
      preferredResponseSpeed = 'fast';
    } else if (avgResponseTime < 3000) {
      preferredResponseSpeed = 'moderate';
    } else {
      preferredResponseSpeed = 'slow';
    }

    const technicalInterestLevel = Math.min(technicalInterestSum / (totalEvents * 50), 1);

    return {
      preferredLanguageStyle,
      averageResponseDetailPreference,
      suggestionAcceptanceRate,
      preferredResponseSpeed,
      technicalInterestLevel
    };
  }
}

export const interactionHistoryAnalyzer = new InteractionHistoryAnalyzer();

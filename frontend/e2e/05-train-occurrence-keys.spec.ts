import { test, expect } from './fixtures';
import { getTrainOccurrenceKey } from '../src/lib/railway/identity';
import { TrainMovement } from '../src/types/railway';

test.describe('Regression: Train Movement Occurrence Keys & Zero Duplicate Key Warnings', () => {
  // Test collection containing multiple legitimate movements of the affected train services
  const MULTI_OCCURRENCE_TRAINS: TrainMovement[] = [
    {
      movement_id: 'MOV-12001-NDLS-01',
      train_id: 'TRN-12001',
      train_number: '12001',
      train_name: 'Bhopal Shatabdi Express',
      station_code: 'NDLS',
      stop_sequence: 1,
      scheduled_departure: '06:00',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12001-MTJ-02',
      train_id: 'TRN-12001',
      train_number: '12001',
      train_name: 'Bhopal Shatabdi Express',
      station_code: 'MTJ',
      stop_sequence: 2,
      scheduled_arrival: '07:20',
      scheduled_departure: '07:25',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12002-RKMP-01',
      train_id: 'TRN-12002',
      train_number: '12002',
      train_name: 'New Delhi Shatabdi Express',
      station_code: 'RKMP',
      stop_sequence: 1,
      scheduled_departure: '14:40',
      entry_station: 'CNB',
      exit_station: 'NDLS',
      direction: 'UP',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12002-BPL-02',
      train_id: 'TRN-12002',
      train_number: '12002',
      train_name: 'New Delhi Shatabdi Express',
      station_code: 'BPL',
      stop_sequence: 2,
      scheduled_arrival: '15:00',
      scheduled_departure: '15:05',
      entry_station: 'CNB',
      exit_station: 'NDLS',
      direction: 'UP',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12004-NDLS-01',
      train_id: 'TRN-12004',
      train_number: '12004',
      train_name: 'Lucknow Swarna Shatabdi',
      station_code: 'NDLS',
      stop_sequence: 1,
      scheduled_departure: '06:10',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12004-GZB-02',
      train_id: 'TRN-12004',
      train_number: '12004',
      train_name: 'Lucknow Swarna Shatabdi',
      station_code: 'GZB',
      stop_sequence: 2,
      scheduled_arrival: '06:45',
      scheduled_departure: '06:47',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-12621-MAS-01',
      train_id: 'TRN-12621',
      train_number: '12621',
      train_name: 'Tamil Nadu Express',
      station_code: 'MAS',
      stop_sequence: 1,
      scheduled_departure: '22:00',
      entry_station: 'CNB',
      exit_station: 'NDLS',
      direction: 'UP',
      priority_tier: 2,
    },
    {
      movement_id: 'MOV-12621-BZA-02',
      train_id: 'TRN-12621',
      train_number: '12621',
      train_name: 'Tamil Nadu Express',
      station_code: 'BZA',
      stop_sequence: 2,
      scheduled_arrival: '03:45',
      scheduled_departure: '03:55',
      entry_station: 'CNB',
      exit_station: 'NDLS',
      direction: 'UP',
      priority_tier: 2,
    },
    {
      movement_id: 'MOV-22436-NDLS-01',
      train_id: 'TRN-22436',
      train_number: '22436',
      train_name: 'Vande Bharat Express',
      station_code: 'NDLS',
      stop_sequence: 1,
      scheduled_departure: '06:00',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
    {
      movement_id: 'MOV-22436-CNB-02',
      train_id: 'TRN-22436',
      train_number: '22436',
      train_name: 'Vande Bharat Express',
      station_code: 'CNB',
      stop_sequence: 2,
      scheduled_arrival: '10:08',
      scheduled_departure: '10:10',
      entry_station: 'NDLS',
      exit_station: 'CNB',
      direction: 'DOWN',
      priority_tier: 1,
    },
  ];

  test('Unit: getTrainOccurrenceKey produces unique, stable keys across multi-movement train services', () => {
    // 1. Verify key uniqueness across collection containing duplicate train_ids
    const keys = MULTI_OCCURRENCE_TRAINS.map((tr, idx) => getTrainOccurrenceKey(tr, idx));
    const uniqueKeys = new Set(keys);
    expect(uniqueKeys.size).toBe(MULTI_OCCURRENCE_TRAINS.length);

    // Specifically verify reported train IDs receive distinct keys
    const trn12001Keys = MULTI_OCCURRENCE_TRAINS.filter((t) => t.train_id === 'TRN-12001').map((t, i) => getTrainOccurrenceKey(t, i));
    expect(trn12001Keys.length).toBe(2);
    expect(trn12001Keys[0]).not.toBe(trn12001Keys[1]);

    const trn12002Keys = MULTI_OCCURRENCE_TRAINS.filter((t) => t.train_id === 'TRN-12002').map((t, i) => getTrainOccurrenceKey(t, i));
    expect(trn12002Keys.length).toBe(2);
    expect(trn12002Keys[0]).not.toBe(trn12002Keys[1]);

    const trn12004Keys = MULTI_OCCURRENCE_TRAINS.filter((t) => t.train_id === 'TRN-12004').map((t, i) => getTrainOccurrenceKey(t, i));
    expect(trn12004Keys.length).toBe(2);
    expect(trn12004Keys[0]).not.toBe(trn12004Keys[1]);

    const trn12621Keys = MULTI_OCCURRENCE_TRAINS.filter((t) => t.train_id === 'TRN-12621').map((t, i) => getTrainOccurrenceKey(t, i));
    expect(trn12621Keys.length).toBe(2);
    expect(trn12621Keys[0]).not.toBe(trn12621Keys[1]);

    const trn22436Keys = MULTI_OCCURRENCE_TRAINS.filter((t) => t.train_id === 'TRN-22436').map((t, i) => getTrainOccurrenceKey(t, i));
    expect(trn22436Keys.length).toBe(2);
    expect(trn22436Keys[0]).not.toBe(trn22436Keys[1]);

    // 2. Stability across repeated calls
    const secondPass = MULTI_OCCURRENCE_TRAINS.map((tr, idx) => getTrainOccurrenceKey(tr, idx));
    expect(secondPass).toEqual(keys);

    // 3. Fallback hierarchy: composite key when movement_id is absent
    const withoutMovementId: TrainMovement = {
      train_id: 'TRN-12001',
      train_number: '12001',
      train_name: 'Bhopal Shatabdi',
      station_code: 'AGC',
      stop_sequence: 3,
    };
    const compositeKey = getTrainOccurrenceKey(withoutMovementId);
    expect(compositeKey).toBe('TRN-12001:AGC:seq-3');

    // 4. Normal unique train scenario
    const singleTrain: TrainMovement = {
      train_id: 'TRN-DEMO-SINGLE',
      train_number: '99999',
      train_name: 'Special Freight Rake',
    };
    expect(getTrainOccurrenceKey(singleTrain)).toBe('TRN-DEMO-SINGLE');
  });

  test('Browser: Time-Space Chart renders multi-movement trains with zero duplicate-key warnings', async ({ page }) => {
    const consoleWarnings: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      // Track React runtime warnings
      if (text.includes('same key') || text.includes('two children with the same key')) {
        consoleWarnings.push(text);
      }
    });

    // Navigate directly to planning workspace with Time-Space subtab
    await page.goto('/planning?subtab=TIMESPACE');
    await page.waitForLoadState('networkidle');

    // If still not active, click the Time-Space subtab button explicitly
    const timeSpaceTab = page.locator('button:has-text("Time-Space")').first();
    if (await timeSpaceTab.isVisible()) {
      await timeSpaceTab.click();
    }

    // Verify Corridor Time-Space Diagram mounts
    await expect(page.locator('text=Corridor Time-Space Diagram')).toBeVisible({ timeout: 15000 });

    // Verify train numbers are visible in the diagram
    await expect(page.locator('text=12004').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=22436').first()).toBeVisible({ timeout: 10000 });

    // Verify ZERO duplicate-key warnings in the browser console
    const duplicateKeyWarnings = consoleWarnings.filter(
      (w) =>
        w.includes('TRN-12002') ||
        w.includes('TRN-12621') ||
        w.includes('TRN-12001') ||
        w.includes('TRN-12004') ||
        w.includes('TRN-22436')
    );
    expect(duplicateKeyWarnings).toHaveLength(0);
    expect(consoleWarnings).toHaveLength(0);

    // Verify stable identity across filter changes
    const dayFilter = page.locator('button:has-text("DAY1")').first();
    if (await dayFilter.isVisible()) {
      await dayFilter.click();
      await page.waitForTimeout(500);

      const allFilter = page.locator('button:has-text("ALL")').first();
      if (await allFilter.isVisible()) {
        await allFilter.click();
        await page.waitForTimeout(500);
      }
    }

    // Verify still zero duplicate key warnings after filter interactions
    expect(consoleWarnings).toHaveLength(0);
  });
});

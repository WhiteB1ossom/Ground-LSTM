# 발표자료 마지막 표와 설정 대응

프로젝트의 「그라운드_회차별 오픈랩 진행 계획_ver a_260909.pdf」 6페이지를 이미지로 확인하여 표준 센서 프로파일을 추가했습니다. 이 PDF가 사용자가 말한 PPT와 같은 자료인지는 확인 대기 중입니다. 기존 임의 단위 합성 실험과 학습 결과는 보존했습니다.

## 표에서 읽은 값

| 센서 | 센싱 범위 | 표의 기준값 | 관측 주기 |
|---|---|---|---|
| 대지전위 a/b | 0~50 V AC | Threshold 1 = 2 | 100 ms |
| 누설전류 | 0.001~1 A | 1 mA = 0.001 A | 1초 |
| 제한소자 온도 a/b/c | 25~150 ℃ | 25 ℃ | 60초 |
| 상대습도 | 20~90% | 60% | **60분** |
| 외기온도 | -20~80 ℃ | 비교값 | **60분** |
| 입력전압 AC | 0~1500 | 사용전압 비교, 참고용 | 1초 |
| 번개센서 | H/L | H=1, L=0 | 100 ms |

모든 행의 표기 바이트 수는 5 bytes입니다. 이는 통신 인코딩이나 전체 MCU 메모리 요구량을 정의하지 않습니다. 대지전위 기준 2의 단위는 같은 행의 V AC 맥락이며, 입력전압 range 셀에는 단위가 따로 적혀 있지 않습니다. 입력전압 프로파일의 V AC 단위는 센서 명칭을 따른 해석입니다.

## 추가한 설정

- `configs/sensors_standard.yaml`: 표의 단위 맥락·범위·주기를 반영한 센서 프로파일.
- `configs/preprocessing_standard.yaml`: 표준 프로파일을 사용하는 입력 검사 설정. raw 위치는 `data/raw/standard`.
- `configs/sensor_standard_reference.yaml`: 표의 원문·기준값·단위 변환·5 bytes·미확인 의미를 보존하는 출처 기록.

기준값은 reference 파일에 보존했습니다. 현재 baseline의 sensor threshold는 숫자가 있으면 자동으로 `>=` 규칙으로 해석됩니다. 하지만 표에는 초과/이상/차이 등의 연산자가 없으므로 표준 sensor profile의 자동 판정 threshold는 아직 `null`입니다. 확인된 값과 비교 방향은 이후 `baseline.threshold_rules`에 명시해야 합니다.

온도 25 ℃를 절대온도 `>=25 ℃`로 해석하면 센싱 범위 25~150 ℃가 전부 위험으로 분류됩니다. 기준 온도 대비 상승량인지, 외기온도 차이인지, 절대온도 기준인지 확인해야 합니다. 누설전류도 기준 1 mA가 센싱 하한과 같으므로 동일하게 비교 방향과 동작 의미를 확인해야 합니다. 이러한 threshold를 임의로 ground_truth label로 바꾸지 않습니다.

## 실제 데이터 검사

측정 파일은 표준 프로파일과 같은 단위로 준비합니다. 예를 들어 current를 mA로 제공받았다면 source adapter에서 A로 명시적으로 변환해야 하며, 숫자 크기를 보고 단위를 추측하지 않습니다.

```powershell
.\.venv-ml\Scripts\python -m src.data.inspect --config configs/preprocessing_standard.yaml --input "실제파일.csv"
```

표의 센싱 범위는 품질 review 기준이며, 범위 밖 값을 잘라내거나 삭제하지 않습니다. 번개센서는 숫자 0/1을 입력하며 H/L 원문이면 명시적인 source adapter가 필요합니다.

## 재학습 전에 필요한 내용

마지막 표는 센서 항목과 기준을 정의하지만 timestamp별 측정값과 ground_truth를 포함하지 않습니다. 따라서 이 표만으로 실측 모델을 학습하거나 정확도를 평가할 수 없습니다.

실제 관측 파일·label 의미를 확인한 후 acquisition kind, 허용 staleness, sequence 길이·stride·purge gap·label horizon을 설정하고 전처리부터 다시 실행해야 합니다. 기존 demo의 습도/외기온도 30초, 임의 단위 scaler와 LSTM은 표준 설정에 사용할 수 없습니다. 표의 60분 주기는 1.6초 demo window만으로 느린 센서의 변화를 학습하기 어렵다는 점도 함께 검토해야 합니다.

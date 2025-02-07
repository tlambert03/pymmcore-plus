import time

import acquire_zarr as aqz
import numpy as np

PATH = "/Users/talley/Desktop/test.zarr"
settings = aqz.StreamSettings(
    store_path=PATH,
    data_type=aqz.DataType.UINT16,
    version=aqz.ZarrVersion.V3,
    max_threads=48,
)

NT = 10
CHUNK_SIZE_PX = 256
FRAME_SHAPE = (2, CHUNK_SIZE_PX * 8, CHUNK_SIZE_PX * 8)
settings.dimensions.extend(
    [
        aqz.Dimension(
            name="t",
            type=aqz.DimensionType.TIME,
            array_size_px=0,
            chunk_size_px=5,
            shard_size_chunks=1,
        ),
        aqz.Dimension(
            name="c",
            type=aqz.DimensionType.CHANNEL,
            array_size_px=FRAME_SHAPE[0],
            chunk_size_px=1,
            shard_size_chunks=1,
        ),
        aqz.Dimension(
            name="y",
            type=aqz.DimensionType.SPACE,
            array_size_px=FRAME_SHAPE[1],
            chunk_size_px=CHUNK_SIZE_PX,
            shard_size_chunks=2,
        ),
        aqz.Dimension(
            name="x",
            type=aqz.DimensionType.SPACE,
            array_size_px=FRAME_SHAPE[2],
            chunk_size_px=CHUNK_SIZE_PX,
            shard_size_chunks=2,
        ),
    ]
)


start = time.perf_counter()
stream = aqz.ZarrStream(settings)
for _i in range(20):
    data = np.random.randint(0, 2**16 - 1, FRAME_SHAPE, dtype=np.uint16)
    t0 = time.perf_counter()
    stream.append(data)
    t1 = time.perf_counter()
    print(f"round {_i}, append time: {t1 - t0}")

end = time.perf_counter()
print(f"total time: {end - start}")
# zarr_group = zarr.open(PATH, mode="r")
# hcs_group = ome_zarr_models.open_ome_zarr(zarr_group)

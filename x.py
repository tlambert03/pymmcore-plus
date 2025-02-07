import time

import numpy as np
import tensorstore as ts


def main() -> None:
    PATH: str = "/Users/talley/Desktop/test2.zarr"
    CHUNK_SIZE_PX: int = 256
    # FRAME_SHAPE corresponds to the non-time dimensions (channel, y, x).
    FRAME_SHAPE: tuple[int, int, int] = (
        2,
        CHUNK_SIZE_PX * 8,
        CHUNK_SIZE_PX * 8,
    )  # (2, 2048, 2048)

    # The overall array is 4D with a "time" dimension that is initially 0.
    initial_shape = [0, FRAME_SHAPE[0], FRAME_SHAPE[1], FRAME_SHAPE[2]]
    # Chunking: time chunks of size 5, channel chunks of 1, and spatial chunks of 256.

    # Create the TensorStore spec for a Zarr v3 array.
    spec: dict = {
        "driver": "zarr3",
        "kvstore": {"driver": "file", "path": PATH},
        "dtype": "uint16",
        "metadata": {
            "zarr_format": 3,
            "shape": initial_shape,
            "data_type": "uint16",
            # Additional metadata (e.g. dimension names) would go here if needed.
        },
    }
    # Open the store (blocking until ready).
    store = ts.open(spec, create=True, delete_existing=True).result()
    write_futures = []
    total_rounds: int = 20
    start_total = time.perf_counter()
    for i in range(total_rounds):
        # Create a new data frame with shape (2, 2048, 2048)
        data = np.random.randint(0, 2**16 - 1, FRAME_SHAPE, dtype=np.uint16)

        # Increase the size of the "time" axis by 1.
        new_time_length = i + 1
        new_shape = (new_time_length, FRAME_SHAPE[0], FRAME_SHAPE[1], FRAME_SHAPE[2])
        # Wait for the resize operation to complete.
        store.resize(exclusive_max=new_shape).result()

        t0 = time.perf_counter()
        # Write the new frame into the newly allocated slice.
        # (We write to the last time index, i.e. index new_time_length - 1.)
        write_futures.append(store[new_time_length - 1, ...].write(data))
        # write_future.result()  # Wait for the write to complete.
        t1 = time.perf_counter()
        print(f"round {i}, append time: {t1 - t0}")

    # Wait for all writes to complete.
    for write_future in write_futures:
        write_future.result()
    end_total = time.perf_counter()
    print(f"total time: {end_total - start_total}")


if __name__ == "__main__":
    main()
